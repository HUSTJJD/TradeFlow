import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from longport.openapi import QuoteContext, Period
from app.core.config import global_config
from app.strategies import Strategy
from app.core.setup import initialize_trading_context, get_strategy_config
from app.data.provider import (
    get_benchmark_returns,
    fetch_history_candles,
    get_stock_lot_sizes,
    get_period,
)
from app.utils.reporting import print_backtest_summary
from app.utils.plotter import create_performance_chart
from app.trading.position import PositionManager
from app.trading.account import PaperAccount
from app.trading.executor import TradeExecutor
from app.core.constants import SignalType

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    事件驱动的回测引擎。
    基于策略信号模拟交易执行。
    """

    def __init__(
        self,
        strategy: Strategy,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.0003,
        position_ratio: float = 1.0,
    ) -> None:
        self.strategy = strategy
        self.initial_capital = initial_capital

        self.account = PaperAccount(
            initial_capital=initial_capital,
            commission_rate=commission_rate,
        )

        self.equity_curve: List[Dict[str, Any]] = []
        self.performance: Dict[str, float] = {}
        self.symbol = ""

        self.position_manager = PositionManager(position_ratio=position_ratio)
        self.executor = TradeExecutor(self.account, self.position_manager)

        self.stock_names: Dict[str, str] = {}

        # 做T频控（每日每股 1-2 次）
        self.t_max_per_symbol_per_day = int(
            global_config.get("strategy.t.max_trades_per_symbol_per_day", 2)
        )
        self._t_daily_counts: Dict[str, Dict[str, Any]] = {}

    def set_stock_names(self, names: Dict[str, str]):
        """设置股票名称映射"""
        self.stock_names = names
        self.account.set_stock_names(names)

    def set_lot_sizes(self, lot_sizes: Dict[str, int]):
        """设置股票最小交易单位"""
        self.executor.set_lot_sizes(lot_sizes)

    def _allow_t_trade(self, symbol: str, current_time: pd.Timestamp) -> bool:
        """做T频控：仅限制 trade_tag=="T" 的信号。"""
        date_str = str(current_time.date())
        daily = self._t_daily_counts.get(symbol)
        if daily is None or daily.get("date") != date_str:
            daily = {"date": date_str, "count": 0}
            self._t_daily_counts[symbol] = daily

        return daily["count"] < self.t_max_per_symbol_per_day

    def _mark_t_trade(self, symbol: str, current_time: pd.Timestamp) -> None:
        date_str = str(current_time.date())
        daily = self._t_daily_counts.get(symbol)
        if daily is None or daily.get("date") != date_str:
            daily = {"date": date_str, "count": 0}
            self._t_daily_counts[symbol] = daily
        daily["count"] += 1

    def run(
        self, data: Dict[str, pd.DataFrame], start_time: Optional[pd.Timestamp] = None
    ) -> None:
        """
        运行回测模拟（支持多股票）。

        Args:
            data: 股票数据字典，键为 symbol，值为历史数据 DataFrame。
            start_time: 开始执行交易的时间。此时间之前的数据用于预热。
        """
        all_timestamps = set()
        for df in data.values():
            all_timestamps.update(df.index)
        sorted_timestamps = sorted(list(all_timestamps))

        for symbol in data:
            data[symbol] = data[symbol].sort_index()

        total_steps = len(sorted_timestamps)
        logger.info(f"开始回测，共 {len(data)} 支股票，{total_steps} 个时间点")

        for i, current_time in enumerate(sorted_timestamps):
            if start_time and current_time < start_time:
                continue

            for symbol, df in data.items():
                if current_time in df.index:
                    current_price = float(df.loc[current_time]["close"])
                    self.account.update_price(symbol, current_price)

            for symbol, df in data.items():
                if current_time not in df.index:
                    continue

                current_data = df.loc[:current_time]
                current_price = float(df.loc[current_time]["close"])

                signal = self.strategy.analyze(symbol, current_data)

                trade_tag = signal.get("trade_tag")
                if trade_tag == "T" and (not self._allow_t_trade(symbol, current_time)):
                    continue

                result = self.executor.execute(signal, symbol, current_time, current_price)

                if trade_tag == "T" and result.get("status") == "SUCCESS":
                    self._mark_t_trade(symbol, current_time)

            equity = self.account.get_total_equity()
            self.equity_curve.append({"time": current_time, "equity": equity})

        self._calculate_performance()

    def _calculate_performance(self) -> None:
        """计算最终性能指标，包括个股收益。"""
        if not self.equity_curve:
            return

        df_equity = pd.DataFrame(self.equity_curve).set_index("time")
        final_equity = float(df_equity.iloc[-1]["equity"])
        total_return = (final_equity - self.initial_capital) / self.initial_capital

        df_equity["max_equity"] = df_equity["equity"].cummax()
        df_equity["drawdown"] = (
            df_equity["equity"] - df_equity["max_equity"]
        ) / df_equity["max_equity"]
        max_drawdown = float(df_equity["drawdown"].min())

        self.performance = {
            "initial_capital": self.initial_capital,
            "final_value": final_equity,
            "total_return": total_return * 100,
            "max_drawdown": max_drawdown * 100,
        }

        trade_stats = self.account.get_trade_stats()
        self.performance.update(trade_stats)

        logger.info("-" * 30)
        logger.info("回测结果摘要")
        logger.info("-" * 30)
        logger.info(f"初始资金: {self.initial_capital:.2f}")
        logger.info(f"最终权益: {final_equity:.2f}")
        logger.info(f"总收益率: {total_return*100:.2f}%")
        logger.info(f"最大回撤: {max_drawdown*100:.2f}%")
        logger.info(f"总交易次数: {len(self.account.trades)} (平仓: {trade_stats['total_trades']})")
        logger.info(f"胜率: {trade_stats['win_rate']*100:.2f}% ({trade_stats['winning_trades']}/{trade_stats['total_trades']})")
        logger.info(f"平均盈亏比: {trade_stats['avg_pnl_ratio']*100:.2f}%")

        self._calculate_symbol_performance()

    def _calculate_symbol_performance(self) -> None:
        """计算并打印个股收益情况"""
        symbol_stats = {}

        for trade in self.account.trades:
            symbol = trade["symbol"]
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {
                    "realized_pnl": 0.0,
                    "commission": 0.0,
                    "buy_amount": 0.0,
                    "sell_amount": 0.0,
                    "wins": 0,
                    "losses": 0,
                    "trades": 0,
                }

            stats = symbol_stats[symbol]
            stats["commission"] += trade["commission"]

            if trade["action"] == SignalType.BUY:
                stats["buy_amount"] += trade["price"] * trade["quantity"]
            elif trade["action"] == SignalType.SELL:
                revenue = trade["price"] * trade["quantity"]
                stats["sell_amount"] += revenue

                if trade.get("position_after", 0) == 0:
                    stats["trades"] += 1
                    if trade.get("profit_ratio", 0) > 0:
                        stats["wins"] += 1
                    else:
                        stats["losses"] += 1

        logger.info("-" * 30)
        logger.info("个股收益详情")
        logger.info("-" * 30)

        for symbol, stats in symbol_stats.items():
            position = self.account.positions.get(symbol, 0)
            current_price = self.account.latest_prices.get(symbol, 0.0)
            market_value = position * current_price

            total_pnl = (
                stats["sell_amount"] + market_value
            ) - stats["buy_amount"] - stats["commission"]

            roi = (
                (total_pnl / stats["buy_amount"]) * 100 if stats["buy_amount"] > 0 else 0.0
            )

            win_rate = (
                (stats["wins"] / stats["trades"]) * 100 if stats["trades"] > 0 else 0.0
            )

            name = self.stock_names.get(symbol, symbol)
            logger.info(
                f"股票: {name:<6} | 总盈亏: {total_pnl:>10.2f} | ROI: {roi:>6.2f}% | "
                f"持仓: {position:>5d} | 市值: {market_value:>10.2f} | "
                f"胜率: {win_rate:>6.2f}% ({stats['wins']}/{stats['trades']})"
            )

            self.performance[f"symbol_{symbol}_pnl"] = total_pnl
            self.performance[f"symbol_{symbol}_roi"] = roi
            self.performance[f"symbol_{symbol}_win_rate"] = win_rate

    def get_results(self) -> Dict[str, Any]:
        """获取回测结果。"""
        return {
            "trades": self.account.trades,
            "equity_curve": self.equity_curve,
            **self.performance,
        }


def _normalize_daily_index(df: pd.DataFrame) -> pd.DataFrame:
    """将日K索引规范到日期 00:00:00，避免与 15m 索引对齐时产生歧义。"""
    if df is None or df.empty:
        return df
    out = df.copy()
    out.index = pd.to_datetime(out.index).normalize()
    return out


def _get_day_range(day: pd.Timestamp) -> Tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(day.date())
    end = start + pd.Timedelta(days=1)
    return start, end


def run_backtest(quote_ctx: QuoteContext, strategy: Strategy) -> None:
    """执行回测流程。"""
    start_time_str = global_config.get("backtest.start_time", "2023-01-01")
    end_time_str = global_config.get("backtest.end_time", "2023-12-31")
    initial_balance = global_config.get("backtest.initial_balance", 100000)
    commission_rate = global_config.get("backtest.commission_rate", 0.0003)
    position_ratio = global_config.get(
        "backtest.position_ratio",
        global_config.get("trading.position_ratio", 0.2),
    )

    try:
        start_date = datetime.strptime(start_time_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_time_str, "%Y-%m-%d").date()
    except ValueError as e:
        logger.error(f"日期格式无效。请使用 YYYY-MM-DD: {e}")
        return

    symbols, stock_names = initialize_trading_context(quote_ctx)
    if not symbols:
        return

    lot_sizes = get_stock_lot_sizes(quote_ctx, symbols)

    strat_config = get_strategy_config()
    period = strat_config["period"]

    warmup_days = 30
    if period in [Period.Day, Period.Week, Period.Month]:
        warmup_days = 365
    elif period in [Period.Min_60, Period.Min_30]:
        warmup_days = 60
    else:
        warmup_days = 10

    logger.info(
        f"回测范围: {start_date} 至 {end_date} (预热期: {warmup_days} 天)\n"
    )

    logger.info("正在加载历史数据...")

    # 多周期回测：日K做波段，15m做T
    mt_cfg = global_config.get("backtest.multi_timeframe", {}) or {}
    mt_enabled = bool(mt_cfg.get("enabled", False))
    swing_tf = str(mt_cfg.get("swing_timeframe", global_config.get("strategy.timeframe", "1d")))
    t_tf = str(mt_cfg.get("t_timeframe", "15m"))

    if mt_enabled:
        swing_period = get_period(swing_tf)
        t_period = get_period(t_tf)

        warmup_days_swing = 365
        warmup_days_t = 60

        data_map_swing: Dict[str, pd.DataFrame] = {}
        data_map_t: Dict[str, pd.DataFrame] = {}

        for symbol in symbols:
            stock_name = stock_names.get(symbol, symbol)
            try:
                df_swing = fetch_history_candles(
                    quote_ctx, symbol, swing_period, start_date, end_date, warmup_days_swing
                )
                df_t = fetch_history_candles(
                    quote_ctx, symbol, t_period, start_date, end_date, warmup_days_t
                )

                df_swing = _normalize_daily_index(df_swing)

                if df_swing.empty or df_t.empty:
                    logger.warning(f"{stock_name} ({symbol}) 多周期数据为空: swing={len(df_swing)}, t={len(df_t)}")
                    continue

                data_map_swing[symbol] = df_swing
                data_map_t[symbol] = df_t.sort_index()

                logger.info(
                    f"已加载 {stock_name} ({symbol}): 日K={len(df_swing)} 条, {t_tf}={len(df_t)} 条"
                )
            except Exception as e:
                logger.error(f"加载 {symbol} 多周期数据出错: {e}")

        if not data_map_swing:
            logger.error("没有可用的多周期回测数据。")
            return

        engine = BacktestEngine(
            strategy,
            initial_capital=initial_balance,
            commission_rate=commission_rate,
            position_ratio=position_ratio,
        )
        engine.set_stock_names(stock_names)
        engine.set_lot_sizes(lot_sizes)

        # --- 多周期事件循环 ---
        # 规则：
        # - 以日K的每个交易日为主循环，先做 SWING 决策（入场/出场/分批止盈）
        # - 同日内，再用 15m K 线推进，仅允许 trade_tag=="T" 的信号触发（策略内部会标记）
        # - 权益曲线按日记录（与原先一致），但交易记录会保留 15m 的精确时间，plot 表格可显示当日多笔交易

        # 收集所有交易日
        all_days = set()
        for df in data_map_swing.values():
            all_days.update(df.index)
        sorted_days = sorted(list(all_days))

        start_ts = pd.Timestamp(start_date)

        for day in sorted_days:
            if day < start_ts:
                continue

            day_start, day_end = _get_day_range(day)

            # 1) 用当日日K更新价格 & 先执行波段信号
            for symbol, df_day in data_map_swing.items():
                if day not in df_day.index:
                    continue

                daily_close = float(df_day.loc[day]["close"])
                engine.account.update_price(symbol, daily_close)

            for symbol, df_day in data_map_swing.items():
                if day not in df_day.index:
                    continue

                daily_slice = df_day.loc[:day]
                daily_close = float(df_day.loc[day]["close"])

                signal = strategy.analyze(symbol, daily_slice)
                if signal.get("trade_tag") == "T":
                    # 日K阶段禁止做T
                    continue

                engine.executor.execute(signal, symbol, day, daily_close)

            # 2) 同日内 15m 推进（仅做T）
            for symbol, df_t in data_map_t.items():
                mask = (df_t.index >= day_start) & (df_t.index < day_end)
                df_intraday = df_t.loc[mask]
                if df_intraday.empty:
                    continue

                for ts in df_intraday.index:
                    if ts < start_ts:
                        continue

                    price = float(df_intraday.loc[ts]["close"])
                    engine.account.update_price(symbol, price)

                    t_slice = df_t.loc[:ts]
                    signal = strategy.analyze(symbol, t_slice)

                    trade_tag = signal.get("trade_tag")
                    if trade_tag != "T":
                        continue

                    if not engine._allow_t_trade(symbol, ts):
                        continue

                    result = engine.executor.execute(signal, symbol, ts, price)
                    if result.get("status") == "SUCCESS":
                        engine._mark_t_trade(symbol, ts)

            equity = engine.account.get_total_equity()
            engine.equity_curve.append({"time": day, "equity": equity})

        engine._calculate_performance()
        results = engine.get_results()

        benchmark_returns = get_benchmark_returns(quote_ctx, start_date, end_date)
        print_backtest_summary(results, start_date, end_date, initial_balance, benchmark_returns)

        plot_config = global_config.get("plot", {})
        if plot_config.get("enabled", False):
            logger.info("正在生成收益率图表...")

            benchmarks_data = {}
            benchmarks_config = plot_config.get("benchmarks", [])

            if not benchmarks_config:
                backtest_benchmarks = global_config.get("backtest.benchmarks", [])
                for symbol in backtest_benchmarks:
                    benchmarks_config.append({"symbol": symbol})

            for bench_cfg in benchmarks_config:
                symbol = bench_cfg.get("symbol")
                if not symbol:
                    continue

                try:
                    df = fetch_history_candles(
                        quote_ctx, symbol, Period.Day, start_date, end_date, 0
                    )
                    if not df.empty:
                        benchmarks_data[symbol] = _normalize_daily_index(df)
                except Exception as e:
                    logger.warning(f"获取基准 {symbol} 数据失败: {e}")

            output_dir = plot_config.get("output_dir", "reports")
            filename = f"backtest_{start_date}_{end_date}.html"

            create_performance_chart(
                equity_curve=results["equity_curve"],
                trades=results["trades"],
                benchmark_data=benchmarks_data,
                config=plot_config,
                output_dir=output_dir,
                filename=filename,
            )

        return

    # --- 单周期回测（保持原逻辑） ---
    data_map = {}

    for symbol in symbols:
        stock_name = stock_names.get(symbol, symbol)

        try:
            df = fetch_history_candles(
                quote_ctx, symbol, period, start_date, end_date, warmup_days
            )

            if df.empty:
                logger.warning(f"{stock_name} ({symbol}) 的数据为空")
                continue

            data_map[symbol] = df
            logger.info(f"已加载 {stock_name} ({symbol}): {len(df)} 条记录")

        except Exception as e:
            logger.error(f"加载 {symbol} 数据出错: {e}")

    if not data_map:
        logger.error("没有可用的回测数据。")
        return

    engine = BacktestEngine(
        strategy,
        initial_capital=initial_balance,
        commission_rate=commission_rate,
        position_ratio=position_ratio,
    )
    engine.set_stock_names(stock_names)
    engine.set_lot_sizes(lot_sizes)

    start_ts = pd.Timestamp(start_date)

    logger.info("开始执行投资组合回测...")

    engine.run(data_map, start_time=start_ts)

    results = engine.get_results()

    benchmark_returns = get_benchmark_returns(quote_ctx, start_date, end_date)

    print_backtest_summary(results, start_date, end_date, initial_balance, benchmark_returns)

    plot_config = global_config.get("plot", {})
    if plot_config.get("enabled", False):
        logger.info("正在生成收益率图表...")

        benchmarks_data = {}
        benchmarks_config = plot_config.get("benchmarks", [])

        if not benchmarks_config:
            backtest_benchmarks = global_config.get("backtest.benchmarks", [])
            for symbol in backtest_benchmarks:
                benchmarks_config.append({"symbol": symbol})

        for bench_cfg in benchmarks_config:
            symbol = bench_cfg.get("symbol")
            if not symbol:
                continue

            try:
                df = fetch_history_candles(
                    quote_ctx, symbol, Period.Day, start_date, end_date, 0
                )
                if not df.empty:
                    benchmarks_data[symbol] = df
            except Exception as e:
                logger.warning(f"获取基准 {symbol} 数据失败: {e}")

        output_dir = plot_config.get("output_dir", "reports")
        filename = f"backtest_{start_date}_{end_date}.html"

        create_performance_chart(
            equity_curve=results["equity_curve"],
            trades=results["trades"],
            benchmark_data=benchmarks_data,
            config=plot_config,
            output_dir=output_dir,
            filename=filename,
        )
