import logging
import time
from datetime import datetime
from typing import Any, Dict, List, cast
from longport.openapi import Period, QuoteContext
from app.core import cfg
from app.engines.engine import Engine
from app.strategies import Strategy

logger = logging.getLogger(__name__)

PeriodLike = Period


class LiveEngine(Engine):
    """实盘执行引擎"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.symbols: List[str] = []
        self.period: PeriodLike = Period.Min_15
        self.history_count: int = 100
        self.interval: int = 60
        self.request_delay: float = 0.5

    def set_live_params(
        self,
        quote_ctx: QuoteContext,
        symbols: List[str],
        period: PeriodLike = Period.Min_15,
        history_count: int = 100,
        interval: int = 60,
        request_delay: float = 0.5,
    ) -> None:
        """设置实盘参数"""
        # 更新 provider 的 quote_ctx，如果需要的话
        # 但通常 Engine 初始化时已经设置了 provider
        if self.provider and isinstance(self.provider, LongPortProvider):
            if not self.provider.quote_ctx:
                self.provider.initialize(quote_ctx=quote_ctx)

        self.symbols = symbols
        self.period = period
        self.history_count = history_count
        self.interval = interval
        self.request_delay = request_delay

    def run(self) -> Dict[str, Any]:
        """运行实盘监控"""
        if not self.symbols:
            logger.error("实盘参数未设置")
            return {}

        # 确保 provider 已初始化
        if isinstance(self.provider, LongPortProvider) and not self.provider.quote_ctx:
            logger.error("Provider 未初始化 (缺少 quote_ctx)")
            return {}

        if not self.initialize(
            self.symbols, self.provider.quote_ctx
        ):  # initialize 仍需 quote_ctx 签名吗？稍后修改
            return {}

        logger.info("开始实盘监控...")

        try:
            while True:
                logger.info(f"开始新的扫描周期: {datetime.now()}")

                data_source = LiveDataSource(
                    provider=self.provider,
                    symbols=self.symbols,
                    period=self.period,
                    history_count=self.history_count,
                    request_delay=self.request_delay,
                )

                for symbol, signal_time, df in data_source.iter_signal_points():
                    stock_name = self.stock_names.get(symbol, symbol)

                    current_price = float(df.iloc[-1]["close"])

                    if self._is_stale(signal_time):
                        logger.debug(f"{symbol} 数据滞后，市场可能休市")
                        continue

                    signal = self.strategy.analyze(symbol, df)
                    if "price" not in signal:
                        signal["price"] = current_price

                    result = self.process_signal(
                        symbol, signal, signal_time, current_price
                    )
                    self.record_equity(signal_time)

                    if result.get("status") == "SUCCESS":
                        self._send_notification(
                            symbol,
                            stock_name,
                            signal,
                            signal_time,
                            current_price,
                            result,
                        )

                logger.info(f"周期完成。等待 {self.interval} 秒...")
                time.sleep(self.interval)

        except KeyboardInterrupt:
            logger.info("程序由用户停止。")
        except Exception as e:
            logger.error(f"实盘交易中发生未处理的异常: {e}")

        return self.get_results()

    def _is_stale(self, signal_time: datetime) -> bool:
        time_diff = datetime.now() - signal_time
        period_seconds = self._get_period_seconds(self.period)
        return time_diff.total_seconds() > (period_seconds * 2 + 300)

    def _get_period_seconds(self, period: PeriodLike) -> int:
        """获取时间周期对应的秒数"""
        period_mapping = {
            Period.Min_1: 60,
            Period.Min_5: 300,
            Period.Min_15: 900,
            Period.Min_30: 1800,
            Period.Min_60: 3600,
            Period.Day: 86400,
        }
        return int(period_mapping.get(period, 900))

