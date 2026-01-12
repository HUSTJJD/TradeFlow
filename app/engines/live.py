import logging
from typing import Any, Dict, List, cast
from longport.openapi import Period, QuoteContext
from app.core.config import global_config
from app.engines.engine import Engine
from app.strategies import Strategy

logger = logging.getLogger(__name__)


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

    def _send_notification(
        self,
        symbol: str,
        stock_name: str,
        signal: Dict[str, Any],
        signal_time: datetime,
        current_price: float,
        result: Dict[str, Any],
    ) -> None:
        """发送交易通知"""
        try:
            from app.notifier.notifier import notifier

            title = f"【信号】{stock_name} ({symbol}) {signal['action']}"
            content = (
                f"代码: {symbol}<br>"
                f"名称: {stock_name}<br>"
                f"时间: {signal_time}<br>"
                f"动作: {signal['action']}<br>"
                f"价格: {current_price}<br>"
                f"原因: {signal['reason']}<br>"
                f"账户状态: 现金={self.account.cash:.2f}, 总权益={self.account.get_total_equity():.2f}"
            )

            notifier.send_message(title, content)
            logger.info(f"发送通知: {title}")

        except Exception as e:
            logger.warning(f"发送通知失败: {e}")


def _load_account_state(engine: LiveEngine) -> None:
    try:
        from app.trading.persistence import AccountPersistence

        persistence = AccountPersistence("simulate/paper_account.json")

        if persistence.load(engine.account):
            logger.info("已加载之前的账户状态")
            logger.info(
                "当前账户状态: 现金=%.2f, 总权益=%.2f",
                engine.account.cash,
                engine.account.get_total_equity(),
            )
            if engine.account.positions:
                logger.info("当前持仓: %s", engine.account.positions)
        else:
            logger.info("未找到之前的账户状态，使用初始账户")

    except Exception as exc:
        logger.warning("加载账户状态失败: %s", exc)


def _save_account_state(engine: LiveEngine) -> None:
    try:
        from app.trading.persistence import AccountPersistence

        persistence = AccountPersistence("simulate/paper_account.json")
        persistence.save(engine.account)
        logger.info("账户状态已保存")

    except Exception as exc:
        logger.warning("保存账户状态失败: %s", exc)


def run_live_trading(quote_ctx: QuoteContext, strategy: Strategy) -> Dict[str, Any]:
    """执行实盘交易监控（Runner entrypoint）。

    方案A：直接读 `global_config`，不再引入额外的 config/service manager 层。
    """

    from app.providers.longport import get_stock_pool
    from app.core.setup import get_strategy_config

    symbols = cast(List[str], get_stock_pool())
    if not symbols:
        logger.error("股票池为空，请先运行universe刷新")
        return {}

    strat_config = get_strategy_config()
    period = cast(Period, strat_config["period"])
    history_count = int(strat_config["history_count"])

    initial_capital = float(
        global_config.get(
            "trading.total_capital",
            global_config.get("trading.initial_balance", 100000.0),
        )
    )
    commission_rate = float(global_config.get("trading.commission_rate", 0.0003))
    position_ratio = float(global_config.get("trading.position_ratio", 0.2))

    monitor_cfg = cast(Dict[str, Any], global_config.get("monitor", {}) or {})
    interval = int(monitor_cfg.get("interval", 60))
    request_delay = float(monitor_cfg.get("request_delay", 0.5))

    logger.info(
        "实盘监控初始化完成。监控 %d 支股票，周期: %d 秒", len(symbols), interval
    )

    engine = LiveEngine(
        quote_ctx=quote_ctx,
        strategy=strategy,
        initial_capital=initial_capital,
        commission_rate=commission_rate,
        position_ratio=position_ratio,
    )

    engine.set_live_params(
        quote_ctx=quote_ctx,
        symbols=symbols,
        period=period,
        history_count=history_count,
        interval=interval,
        request_delay=request_delay,
    )

    if not engine.initialize(symbols, quote_ctx):
        logger.error("实盘引擎初始化失败")
        return {}

    _load_account_state(engine)

    logger.info("开始实盘监控...")

    try:
        results = engine.run()
        _save_account_state(engine)
        return results

    except KeyboardInterrupt:
        logger.info("程序由用户停止。")
        _save_account_state(engine)
        return engine.get_results()

    except Exception as exc:
        logger.error("实盘交易中发生未处理的异常: %s", exc)
        _save_account_state(engine)
        return engine.get_results()
