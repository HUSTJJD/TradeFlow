import logging
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional, cast
from dataclasses import dataclass
from longport.openapi import QuoteContext, Period

from app.core.config import global_config
from app.strategies import Strategy
from app.trading.position import PositionManager
from app.engines.engine import BacktestEngine
from app.providers.longport import (
    get_stock_names,
    get_stock_lot_sizes,
    fetch_history_candles,
    get_benchmark_returns,
)
from app.utils.reporting import print_backtest_summary
from app.utils.plotter import create_performance_chart

logger = logging.getLogger(__name__)


def _normalize_daily_index(df: pd.DataFrame) -> pd.DataFrame:
    """将日K索引规范到日期 00:00:00，避免与 15m 索引对齐时产生歧义。"""
    if df.empty:
        return df
    out = df.copy()
    # pandas typing stubs sometimes miss DatetimeIndex.normalize; normalize via to_datetime.
    out.index = pd.to_datetime(out.index).map(lambda x: x.normalize())
    return out


def _get_day_range(day: Any) -> tuple[pd.Timestamp, pd.Timestamp]:
    """获取指定日期的开始和结束时间"""
    day_ts = pd.Timestamp(day)
    if day_ts is pd.NaT:
        raise ValueError("day cannot be NaT")

    start = pd.Timestamp(
        cast(datetime, day_ts.to_pydatetime()).replace(hour=0, minute=0, second=0, microsecond=0)
    )
    if start is pd.NaT:
        raise ValueError("start cannot be NaT")

    end = start + pd.Timedelta(days=1)
    if end is pd.NaT:
        raise ValueError("end cannot be NaT")

    return cast(pd.Timestamp, start), cast(pd.Timestamp, end)


@dataclass(frozen=True)
class BacktestConfig:
    start_time: str
    end_time: str
    initial_balance: float
    commission_rate: float
    position_ratio: float
    warmup_days_daily: int
    warmup_days_hourly: int
    warmup_days_intraday: int

    multi_timeframe_enabled: bool
    swing_timeframe: str
    t_timeframe: str

    universe_lookback_days: int
    universe_refresh_every_n_days: int

    @classmethod
    def from_global_config(cls) -> "BacktestConfig":
        warmup_cfg = global_config.get("backtest.warmup_days", {}) or {}
        mt_cfg = global_config.get("backtest.multi_timeframe", {}) or {}
        refresh_cfg = global_config.get("universe.refresh", {}) or {}

        return cls(
            start_time=str(global_config.get("backtest.start_time", "2023-01-01")),
            end_time=str(global_config.get("backtest.end_time", "2023-12-31")),
            initial_balance=float(global_config.get("backtest.initial_balance", 100000.0)),
            commission_rate=float(global_config.get("backtest.commission_rate", 0.0003)),
            position_ratio=float(global_config.get("backtest.position_ratio", 0.2)),
            warmup_days_daily=int(warmup_cfg.get("daily", 365)),
            warmup_days_hourly=int(warmup_cfg.get("hourly", 60)),
            warmup_days_intraday=int(warmup_cfg.get("intraday", 30)),
            multi_timeframe_enabled=bool(mt_cfg.get("enabled", False)),
            swing_timeframe=str(mt_cfg.get("swing_timeframe", "1d")),
            t_timeframe=str(mt_cfg.get("t_timeframe", "15m")),
            universe_lookback_days=int(refresh_cfg.get("lookback_days", 120)),
            universe_refresh_every_n_days=int(global_config.get("backtest.universe_refresh_every_n_days", 1)),
        )


class BacktestUniversePoolBuilder:
    def __init__(
        self,
        quote_ctx: QuoteContext,
        max_symbols: int,
        one_per_industry: bool,
        lookback_days: int,
        batch_size: int,
    ) -> None:
        self._quote_ctx = quote_ctx
        self._max_symbols = int(max_symbols)
        self._one_per_industry = bool(one_per_industry)
        self._lookback_days = int(lookback_days)
        self._batch_size = int(batch_size)

    def build_pool(self, all_symbols: List[str], as_of: date) -> List[str]:
        from app.engines.universe_refresh import (
            FundamentalQualityScorer,
            PlaceholderNewsScorer,
            TechnicalMomentumScorer,
            UniverseCandidateSelector,
            UniverseCompositeScorer,
            UniverseScoringService,
            UniverseScoringWeights,
            VolatilityHotnessScorer,
        )

        name_map: Dict[str, str] = {}
        industry_map: Dict[str, str] = {}
        board_map: Dict[str, str] = {}
        fundamentals_map: Dict[str, Dict[str, Any]] = {}

        weights = UniverseScoringWeights.from_config()
        composite = UniverseCompositeScorer(
            weights=weights,
            technical=TechnicalMomentumScorer(),
            sentiment=VolatilityHotnessScorer(),
            news=PlaceholderNewsScorer(),
            fundamental=FundamentalQualityScorer(),
        )

        scoring_service = UniverseScoringService(composite_scorer=composite)

        candidates = scoring_service.build_candidates(
            quote_ctx=self._quote_ctx,
            symbols=all_symbols,
            name_map=name_map,
            industry_map=industry_map,
            board_map=board_map,
            fundamentals_map=fundamentals_map,
            lookback_days=self._lookback_days,
            batch_size=self._batch_size,
        )

        selector = UniverseCandidateSelector(
            max_symbols=self._max_symbols,
            one_per_industry=self._one_per_industry,
        )
        return selector.select(candidates)


class BacktestDailyWorkflow:
    def __init__(
        self,
        quote_ctx: QuoteContext,
        engine: BacktestEngine,
        pool_builder: BacktestUniversePoolBuilder,
        symbols_universe: List[str],
        period: Period,
        warmup_days: int,
    ) -> None:
        self._quote_ctx = quote_ctx
        self._engine = engine
        self._pool_builder = pool_builder
        self._symbols_universe = symbols_universe
        self._period = period
        self._warmup_days = int(warmup_days)

    def run(self, start_date: date, end_date: date) -> Dict[str, Any]:
        logger.info(
            "Backtest daily workflow enabled: close-phase universe scoring + open-phase execution"
        )

        current = start_date
        pool_cache: Dict[str, List[str]] = {}

        while current <= end_date:
            pool = pool_cache.get(str(current))
            if pool is None:
                pool = self._pool_builder.build_pool(self._symbols_universe, as_of=current)
                pool_cache[str(current)] = pool

            if not pool:
                logger.warning(f"{current}: pool is empty, skip")
                current = current + timedelta(days=1)
                continue

            logger.info(f"{current}: selected pool size={len(pool)}")

            data_map = self._load_day_data(pool, day=current, start_date=start_date, end_date=end_date)
            if data_map:
                self._engine.set_data(data_map)

                start_ts_any = pd.Timestamp(datetime.combine(current, datetime.min.time()))
                if start_ts_any is pd.NaT:
                    raise ValueError("start_ts cannot be NaT")

                start_ts = cast(pd.Timestamp, start_ts_any)
                self._engine.run(start_time=start_ts)

            current = current + timedelta(days=1)

        return self._engine.get_results()

    def _load_day_data(
        self, symbols: List[str], day: date, start_date: date, end_date: date
    ) -> Dict[str, pd.DataFrame]:
        # Load once for the whole backtest period to keep engine order stable.
        data_map: Dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            try:
                df = fetch_history_candles(
                    self._quote_ctx,
                    symbol,
                    self._period,
                    start_date,
                    end_date,
                    self._warmup_days,
                )
                if df.empty:
                    continue
                data_map[symbol] = df
            except Exception as e:
                logger.debug(f"load {symbol} failed: {e}")
        return data_map


class BacktestService:
    def __init__(self, quote_ctx: QuoteContext, strategy: Strategy, config: BacktestConfig) -> None:
        self._quote_ctx = quote_ctx
        self._strategy = strategy
        self._config = config

    def run(self) -> Dict[str, Any]:
        start_date, end_date = self._parse_date_range()

        from app.providers.longport import load_cn_universe_symbols, load_hkconnect_universe_symbols

        universe_items: List[Dict[str, Any]] = []
        universe_items.extend(load_cn_universe_symbols())
        universe_items.extend(load_hkconnect_universe_symbols())

        symbols_universe = sorted({cast(str, r.get("symbol") or "") for r in universe_items if r.get("symbol")})
        if not symbols_universe:
            logger.error("Universe symbols are empty. Run run_universe_symbols_refresh() first.")
            return {}

        from app.core.setup import get_strategy_config

        strat_config = get_strategy_config()
        period = cast(Period, strat_config["period"])
        warmup_days = self._resolve_warmup_days(period)

        selector_cfg = global_config.get("universe.selector", {}) or {}
        max_symbols = int(selector_cfg.get("max_symbols", 5))
        one_per_industry = bool(selector_cfg.get("one_per_industry", True))

        data_cfg = global_config.get("data", {}) or {}
        batch_size = int(data_cfg.get("batch_size", 200))

        if self._config.multi_timeframe_enabled:
            # Keep existing behavior for multi-timeframe mode.
            logger.info("Multi-timeframe backtest uses cached pool behavior for now.")
            from app.providers.longport import get_stock_pool

            symbols = get_stock_pool()
            if not symbols:
                logger.error("股票池为空，请先运行universe刷新")
                return {}

            stock_names = get_stock_names(self._quote_ctx, symbols)
            lot_sizes = get_stock_lot_sizes(self._quote_ctx, symbols)

            return self._run_multi_timeframe_backtest(
                symbols=symbols,
                stock_names=stock_names,
                lot_sizes=lot_sizes,
                start_date=start_date,
                end_date=end_date,
            )

        # Daily workflow: close-phase build pool, open-phase execute.
        pool_builder = BacktestUniversePoolBuilder(
            quote_ctx=self._quote_ctx,
            max_symbols=max_symbols,
            one_per_industry=one_per_industry,
            lookback_days=self._config.universe_lookback_days,
            batch_size=batch_size,
        )

        # Engine initializes on full universe to keep name/lot size consistent.
        engine = self._create_engine(symbols_universe)

        workflow = BacktestDailyWorkflow(
            quote_ctx=self._quote_ctx,
            engine=engine,
            pool_builder=pool_builder,
            symbols_universe=symbols_universe,
            period=period,
            warmup_days=warmup_days,
        )

        results = workflow.run(start_date=start_date, end_date=end_date)

        benchmark_returns = get_benchmark_returns(self._quote_ctx, start_date, end_date)
        print_backtest_summary(results, start_date, end_date, self._config.initial_balance, benchmark_returns)
        _generate_performance_chart(results, start_date, end_date)

        return results

    def _parse_date_range(self) -> tuple[date, date]:
        try:
            start_date = datetime.strptime(self._config.start_time, "%Y-%m-%d").date()
            end_date = datetime.strptime(self._config.end_time, "%Y-%m-%d").date()
            return start_date, end_date
        except ValueError as e:
            raise ValueError(f"日期格式无效。请使用 YYYY-MM-DD: {e}")

    def _resolve_warmup_days(self, period: Period) -> int:
        if period in [Period.Day, Period.Week, Period.Month]:
            return int(self._config.warmup_days_daily)
        if period in [Period.Min_60, Period.Min_30]:
            return int(self._config.warmup_days_hourly)
        return int(self._config.warmup_days_intraday)

    def _run_single_timeframe_backtest(
        self,
        symbols: List[str],
        stock_names: Dict[str, str],
        lot_sizes: Dict[str, int],
        start_date: date,
        end_date: date,
        warmup_days: int,
        period: Period,
    ) -> Dict[str, Any]:
        logger.info("正在加载历史数据...")

        data_map: Dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            stock_name = stock_names.get(symbol, symbol)

            try:
                df = fetch_history_candles(
                    self._quote_ctx, symbol, period, start_date, end_date, warmup_days
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
            return {}

        engine = self._create_engine(symbols)
        engine.set_data(data_map)

        logger.info("开始执行投资组合回测...")
        results = engine.run()

        benchmark_returns = get_benchmark_returns(self._quote_ctx, start_date, end_date)

        print_backtest_summary(results, start_date, end_date, self._config.initial_balance, benchmark_returns)
        _generate_performance_chart(results, start_date, end_date)

        return results

    def _run_multi_timeframe_backtest(
        self,
        symbols: List[str],
        stock_names: Dict[str, str],
        lot_sizes: Dict[str, int],
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        logger.info("运行多周期回测模式（日K波段 + 15m做T）")

        from app.providers.longport import get_period

        swing_period = cast(Period, get_period(self._config.swing_timeframe))
        t_period = cast(Period, get_period(self._config.t_timeframe))

        warmup_days_swing = 365
        warmup_days_t = 60

        data_map_swing: Dict[str, pd.DataFrame] = {}
        data_map_t: Dict[str, pd.DataFrame] = {}

        for symbol in symbols:
            stock_name = stock_names.get(symbol, symbol)

            try:
                df_swing = fetch_history_candles(
                    self._quote_ctx, symbol, swing_period, start_date, end_date, warmup_days_swing
                )
                df_t = fetch_history_candles(
                    self._quote_ctx, symbol, t_period, start_date, end_date, warmup_days_t
                )

                df_swing = _normalize_daily_index(df_swing)

                if df_swing.empty or df_t.empty:
                    logger.warning(
                        f"{stock_name} ({symbol}) 多周期数据为空: swing={len(df_swing)}, t={len(df_t)}"
                    )
                    continue

                data_map_swing[symbol] = df_swing
                data_map_t[symbol] = df_t.sort_index()

                logger.info(
                    f"已加载 {stock_name} ({symbol}): 日K={len(df_swing)} 条, {self._config.t_timeframe}={len(df_t)} 条"
                )

            except Exception as e:
                logger.error(f"加载 {symbol} 多周期数据出错: {e}")

        if not data_map_swing:
            logger.error("没有可用的多周期回测数据。")
            return {}

        engine = self._create_engine(symbols)

        results = _run_multi_timeframe_simulation(engine, data_map_swing, data_map_t, start_date, end_date)

        benchmark_returns = get_benchmark_returns(self._quote_ctx, start_date, end_date)

        print_backtest_summary(results, start_date, end_date, self._config.initial_balance, benchmark_returns)
        _generate_performance_chart(results, start_date, end_date)

        return results

    def _create_engine(self, symbols: List[str]) -> BacktestEngine:
        position_manager = PositionManager(position_ratio=float(self._config.position_ratio))
        engine = BacktestEngine(
            quote_ctx=self._quote_ctx,
            strategy=self._strategy,
            position_manager=position_manager,
            initial_capital=float(self._config.initial_balance),
            commission_rate=float(self._config.commission_rate),
            position_ratio=float(self._config.position_ratio),
        )

        if not engine.initialize(symbols, self._quote_ctx):
            raise RuntimeError("回测引擎初始化失败")

        return engine


def _run_multi_timeframe_simulation(
    engine: BacktestEngine,
    data_map_swing: Dict[str, pd.DataFrame],
    data_map_t: Dict[str, pd.DataFrame],
    start_date: date,
    end_date: date,
) -> Dict[str, Any]:
    """运行多周期模拟"""
    # 收集所有交易日
    all_days: set[pd.Timestamp] = set()
    for df in data_map_swing.values():
        for idx in df.index:
            ts = pd.Timestamp(idx)
            if ts is pd.NaT:
                continue
            assert ts is not pd.NaT
            all_days.add(cast(pd.Timestamp, ts))
    sorted_days = sorted(all_days)
    
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
            
            signal = engine.strategy.analyze(symbol, daily_slice)
            if signal.get("trade_tag") == "T":
                # 日K阶段禁止做T
                continue
            
            engine.process_signal(symbol, signal, day, daily_close)
        
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
                signal = engine.strategy.analyze(symbol, t_slice)
                
                trade_tag = signal.get("trade_tag")
                if trade_tag != "T":
                    continue
                
                engine.process_signal(symbol, signal, ts, price)
        
        # 记录权益
        engine.record_equity(day)
    
    return engine.get_results()


def _generate_performance_chart(
    results: Dict[str, Any], start_date: date, end_date: date
) -> None:
    """生成性能图表"""
    plot_config = global_config.get("plot", {})
    if not plot_config.get("enabled", False):
        return
    
    logger.info("正在生成收益率图表...")
    
    # 获取基准数据
    benchmarks_data = {}
    benchmarks_config = plot_config.get("benchmarks", [])
    
    if not benchmarks_config:
        backtest_benchmarks = global_config.get("backtest.benchmarks", [])
        for symbol in backtest_benchmarks:
            benchmarks_config.append({"symbol": symbol})
    
    output_dir = plot_config.get("output_dir", "reports")
    filename = f"backtest_{start_date}_{end_date}.html"
    
    create_performance_chart(
        equity_curve=results.get("equity_curve", []),
        trades=results.get("trades", []),
        benchmark_data=benchmarks_data,
        config=plot_config,
        output_dir=output_dir,
        filename=filename,
    )


def run_backtest(quote_ctx: QuoteContext, strategy: Strategy) -> Dict[str, Any]:
    """执行回测流程（Runner entrypoint）。"""

    config = BacktestConfig.from_global_config()

    try:
        return BacktestService(quote_ctx=quote_ctx, strategy=strategy, config=config).run()
    except Exception as e:
        logger.error(str(e))
        return {}
