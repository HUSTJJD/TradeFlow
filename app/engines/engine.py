from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, cast, Iterable
from datetime import datetime
import pandas as pd
import logging
import time
from longport.openapi import QuoteContext, Period
from app.core.constants import SignalType, SignalType, TradeMode
from app.strategies import Strategy
from app.trading.account import PaperAccount
from app.trading.executor import TradeExecutor
from app.trading.position import PositionManager
from app.trading.manager import TradeManager
from app.providers.longport import get_stock_names, get_stock_lot_sizes

logger = logging.getLogger(__name__)

PeriodLike = Any


class MarketDataSource(ABC):
    """Market data source abstraction for engine runs."""

    @abstractmethod
    def iter_signal_points(self) -> Iterable[tuple[str, datetime, pd.DataFrame]]:
        """Yield (symbol, signal_time, slice_df) for analysis."""
        raise NotImplementedError

    @abstractmethod
    def get_latest_price(self, symbol: str, signal_time: datetime) -> float:
        raise NotImplementedError


class BacktestDataSource(MarketDataSource):
    def __init__(self, data: Dict[str, pd.DataFrame], start_time: Optional[pd.Timestamp] = None) -> None:
        self._data = {k: v.sort_index() for k, v in data.items()}
        self._start_time = start_time

        all_timestamps: set[Any] = set()
        for df in self._data.values():
            all_timestamps.update(df.index)
        self._sorted_timestamps = sorted(all_timestamps)

    def iter_signal_points(self) -> Iterable[tuple[str, datetime, pd.DataFrame]]:
        for ts in self._sorted_timestamps:
            if self._start_time is not None and ts < self._start_time:
                continue

            for symbol, df in self._data.items():
                if ts not in df.index:
                    continue

                ts_pd = pd.Timestamp(ts)
                if ts_pd is pd.NaT:
                    continue
                yield symbol, cast(datetime, ts_pd.to_pydatetime()), df.loc[:ts]

    def get_latest_price(self, symbol: str, signal_time: datetime) -> float:
        df = self._data[symbol]
        ts = pd.Timestamp(signal_time)
        if ts is pd.NaT:
            raise ValueError("signal_time cannot be NaT")
        return float(df.loc[ts]["close"])


class LiveDataSource(MarketDataSource):
    def __init__(
        self,
        quote_ctx: QuoteContext,
        symbols: List[str],
        period: PeriodLike,
        history_count: int,
        request_delay: float,
    ) -> None:
        self._quote_ctx = quote_ctx
        self._symbols = symbols
        self._period = period
        self._history_count = history_count
        self._request_delay = request_delay

    def iter_signal_points(self) -> Iterable[tuple[str, datetime, pd.DataFrame]]:
        from app.providers.longport import fetch_candles

        for symbol in self._symbols:
            df = fetch_candles(self._quote_ctx, symbol, self._period, self._history_count)
            if df.empty:
                time.sleep(self._request_delay)
                continue

            last_index = df.index.to_list()[-1]
            ts = pd.Timestamp(last_index)
            if ts is pd.NaT:
                time.sleep(self._request_delay)
                continue

            yield symbol, cast(datetime, ts.to_pydatetime()), df
            time.sleep(self._request_delay)

    def get_latest_price(self, symbol: str, signal_time: datetime) -> float:
        # Live mode uses latest candle close from the slice itself.
        # Caller passes slice_df; we keep API for symmetry but not used.
        raise NotImplementedError

class BacktestEngine(ExecutionEngine):
    """回测执行引擎"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data: Dict[str, pd.DataFrame] = {}

    def set_data(self, data: Dict[str, pd.DataFrame]) -> None:
        """设置回测数据"""
        self.data = data

    def run(self, start_time: Optional[pd.Timestamp] = None) -> Dict[str, Any]:
        """运行回测"""
        if not self.data:
            logger.error("回测数据为空")
            return {}

        data_source = BacktestDataSource(self.data, start_time=start_time)
        logger.info(f"开始回测，共 {len(self.data)} 支股票")

        for symbol, current_time, current_data in data_source.iter_signal_points():
            current_price = float(current_data.iloc[-1]["close"])
            signal = self.strategy.analyze(symbol, current_data)

            result = self.process_signal(symbol, signal, current_time, current_price)
            if result.get("status") == "SUCCESS":
                logger.debug(f"{symbol} 在 {current_time} 执行 {signal.get('action')}")

            self.record_equity(current_time)

        logger.info("回测完成")
        return self.get_results()


class LiveEngine(ExecutionEngine):
    """实盘执行引擎"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.quote_ctx: Optional[QuoteContext] = None
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
        self.quote_ctx = quote_ctx
        self.symbols = symbols
        self.period = period
        self.history_count = history_count
        self.interval = interval
        self.request_delay = request_delay

    def run(self) -> Dict[str, Any]:
        """运行实盘监控"""
        if not self.quote_ctx or not self.symbols:
            logger.error("实盘参数未设置")
            return {}

        if not self.initialize(self.symbols, self.quote_ctx):
            return {}

        logger.info("开始实盘监控...")

        try:
            while True:
                logger.info(f"开始新的扫描周期: {datetime.now()}")

                data_source = LiveDataSource(
                    quote_ctx=self.quote_ctx,
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

                    result = self.process_signal(symbol, signal, signal_time, current_price)
                    self.record_equity(signal_time)

                    if result.get("status") == "SUCCESS":
                        self._send_notification(symbol, stock_name, signal, signal_time, current_price, result)

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
            from app.utils.notifier import notifier

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



class Engine(ABC):
    """策略执行引擎抽象基类，定义统一的策略执行接口。"""
    def __init__(
        self,
        quote_ctx: QuoteContext,
        strategy: Strategy):
        self._quote_ctx = quote_ctx
        self._strategy = strategy
        self.create_account()
        
        self.t_daily_counts = {}
        self.t_max_per_symbol_per_day = 1

    @abstractmethod
    def create_account(self) -> None:
        """交易账户"""
        self._account = PaperAccount()

    @abstractmethod
    def create_executor(self) -> None:
        """交易执行器"""
        self._executor = PaperExecutor()

    @abstractmethod
    def run(self) -> Dict[str, Any]:
        """运行策略执行引擎"""
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """清理资源"""
        self.create_account()
        logger.info("策略执行引擎已清理")

    def _allow_t_trade(self, symbol: str, current_time: datetime) -> bool:
        """做T频控：仅限制 trade_tag==\"T\" 的信号。"""
        date_str = str(current_time.date())
        daily = self.t_daily_counts.get(symbol)
        if daily is None or daily.get("date") != date_str:
            daily = {"date": date_str, "count": 0}
            self.t_daily_counts[symbol] = daily

        return int(daily.get("count", 0)) < self.t_max_per_symbol_per_day

    def _mark_t_trade(self, symbol: str, current_time: datetime) -> None:
        """标记做T交易"""
        date_str = str(current_time.date())
        daily = self.t_daily_counts.get(symbol)
        if daily is None or daily.get("date") != date_str:
            daily = {"date": date_str, "count": 0}
            self.t_daily_counts[symbol] = daily
        daily["count"] = int(daily.get("count", 0)) + 1

    def process_signal(
        self,
        symbol: str,
        signal: Dict[str, Any],
        current_time: datetime,
        current_price: float,
    ) -> Dict[str, Any]:
        """处理单个信号"""

        # 更新价格
        self._account.update_price(symbol, current_price)

        # 做T频控检查
        trade_tag = signal.get("trade_tag")
        if trade_tag == "T" and not self._allow_t_trade(symbol, current_time):
            return {"status": "SKIPPED", "reason": "做T频控限制"}

        # 执行交易
        result = self._executor.execute(signal, symbol, current_time, current_price)

        # 记录做T交易
        if trade_tag == "T" and result.get("status") == "SUCCESS":
            self._mark_t_trade(symbol, current_time)

        return result

    def record_equity(self, timestamp: datetime) -> None:
        """记录当前权益"""
        equity = self._account.get_total_equity()
        self.equity_curve.append({"time": timestamp, "equity": equity})

    def get_performance(self) -> Dict[str, Any]:
        """获取性能指标"""
        if not self.equity_curve:
            return {}
        df_equity = pd.DataFrame(self.equity_curve).set_index("time")
        final_equity = float(df_equity.iloc[-1]["equity"])
        total_return = (final_equity - self.initial_capital) / self.initial_capital

        df_equity["max_equity"] = df_equity["equity"].cummax()
        df_equity["drawdown"] = (df_equity["equity"] - df_equity["max_equity"]) / df_equity["max_equity"]
        max_drawdown = float(df_equity["drawdown"].min())

        trade_stats = self._account.get_trade_stats()

        return {
            "initial_capital": self.initial_capital,
            "final_value": final_equity,
            "total_return": total_return * 100,
            "max_drawdown": max_drawdown * 100,
            **trade_stats,
        }

    def get_results(self) -> Dict[str, Any]:
        """获取完整结果"""
        return {
            "trades": self._account.trades,
            "equity_curve": self.equity_curve,
            "performance": self.get_performance(),
            "positions": self._account.positions,
            "cash": self._account.cash,
        }



def create_engine(engine_type: TradeMode, quote_ctx: QuoteContext, strategy: Strategy) -> Engine:
    """创建执行引擎"""
    if engine_type == TradeMode.BACKTEST:
        return BacktestEngine(quote_ctx=quote_ctx, strategy=strategy)
    elif engine_type == TradeMode.LIVE:
        return LiveEngine(quote_ctx=quote_ctx, strategy=strategy)
    elif engine_type == TradeMode.PAPER:
        return PaperEngine(quote_ctx=quote_ctx, strategy=strategy)
    else:
        raise ValueError(f"Invalid engine type: {engine_type}")
