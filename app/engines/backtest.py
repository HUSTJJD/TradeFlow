import logging
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional, cast
from longport.openapi import QuoteContext, Period

from app.core import cfg
from app.strategies import Strategy
from app.engines.engine import Engine
from app.providers.longport import LongPortProvider
from app.utils.reporting import print_backtest_summary
from app.utils.plotter import create_performance_chart

logger = logging.getLogger(__name__)


class BacktestEngine(Engine):
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
        cast(datetime, day_ts.to_pydatetime()).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    )
    if start is pd.NaT:
        raise ValueError("start cannot be NaT")

    end = start + pd.Timedelta(days=1)
    if end is pd.NaT:
        raise ValueError("end cannot be NaT")

    return cast(pd.Timestamp, start), cast(pd.Timestamp, end)


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
                pool = self._pool_builder.build_pool(
                    self._symbols_universe, as_of=current
                )
                pool_cache[str(current)] = pool

            if not pool:
                logger.warning(f"{current}: pool is empty, skip")
                current = current + timedelta(days=1)
                continue

            logger.info(f"{current}: selected pool size={len(pool)}")

            data_map = self._load_day_data(
                pool, day=current, start_date=start_date, end_date=end_date
            )
            if data_map:
                self._engine.set_data(data_map)

                start_ts_any = pd.Timestamp(
                    datetime.combine(current, datetime.min.time())
                )
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

        provider = LongPortProvider()
        provider.initialize(quote_ctx=self._quote_ctx)

        for symbol in symbols:
            try:
                pre_start_date = start_date - timedelta(days=self._warmup_days)
                df = provider.get_data(
                    symbol,
                    period=self._period,
                    start_date=pre_start_date,
                    end_date=end_date,
                )
                if df is None or df.empty:
                    continue
                data_map[symbol] = df
            except Exception as e:
                logger.debug(f"load {symbol} failed: {e}")
        return data_map


def _resolve_warmup_days(period: Period) -> int:
    warmup_cfg = cfg.backtest.warmup_days
    if period in [Period.Day, Period.Week, Period.Month]:
        return int(warmup_cfg.get("daily", 365))
    if period in [Period.Min_60, Period.Min_30]:
        return warmup_cfg.hourly
    return int(warmup_cfg.get("intraday", 30))


def _create_engine(
    quote_ctx: QuoteContext, strategy: Strategy, symbols: List[str]
) -> BacktestEngine:
    initial_balance = float(cfg.get("backtest.initial_balance", 100000.0))
    commission_rate = float(cfg.get("backtest.commission_rate", 0.0003))
    position_ratio = float(cfg.get("backtest.position_ratio", 0.2))

    engine = BacktestEngine(
        quote_ctx=quote_ctx,
        strategy=strategy,
        initial_capital=initial_balance,
        commission_rate=commission_rate,
        position_ratio=position_ratio,
    )

    if not engine.initialize(symbols, quote_ctx):
        raise RuntimeError("回测引擎初始化失败")

    return engine


def _run_single_timeframe_backtest(
    quote_ctx: QuoteContext,
    strategy: Strategy,
    symbols: List[str],
    stock_names: Dict[str, str],
    start_date: date,
    end_date: date,
    warmup_days: int,
    period: Period,
) -> Dict[str, Any]:
    logger.info("正在加载历史数据...")

    provider = LongPortProvider()
    provider.initialize(quote_ctx=quote_ctx)

    data_map: Dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        stock_name = stock_names.get(symbol, symbol)

        try:
            pre_start_date = start_date - timedelta(days=warmup_days)
            df = provider.get_data(
                symbol, period=period, start_date=pre_start_date, end_date=end_date
            )

            if df is None or df.empty:
                logger.warning(f"{stock_name} ({symbol}) 的数据为空")
                continue

            data_map[symbol] = df
            logger.info(f"已加载 {stock_name} ({symbol}): {len(df)} 条记录")

        except Exception as e:
            logger.error(f"加载 {symbol} 数据出错: {e}")

    if not data_map:
        logger.error("没有可用的回测数据。")
        return {}

    engine = _create_engine(quote_ctx, strategy, symbols)
    engine.set_data(data_map)

    logger.info("开始执行投资组合回测...")
    results = engine.run()

    initial_balance = float(cfg.get("backtest.initial_balance", 100000.0))
    benchmark_returns = provider.get_benchmark_returns(start_date, end_date)

    print_backtest_summary(
        results, start_date, end_date, initial_balance, benchmark_returns
    )
    _generate_performance_chart(results, start_date, end_date)

    return results


def _run_multi_timeframe_backtest(
    quote_ctx: QuoteContext,
    strategy: Strategy,
    symbols: List[str],
    stock_names: Dict[str, str],
    start_date: date,
    end_date: date,
) -> Dict[str, Any]:
    logger.info("运行多周期回测模式（日K波段 + 15m做T）")

    from app.providers.longport import get_period

    provider = LongPortProvider()
    provider.initialize(quote_ctx=quote_ctx)

    mt_cfg = cfg.get("backtest.multi_timeframe", {}) or {}
    swing_timeframe = str(mt_cfg.get("swing_timeframe", "1d"))
    t_timeframe = str(mt_cfg.get("t_timeframe", "15m"))

    swing_period = cast(Period, get_period(swing_timeframe))
    t_period = cast(Period, get_period(t_timeframe))

    warmup_days_swing = 365
    warmup_days_t = 60

    data_map_swing: Dict[str, pd.DataFrame] = {}
    data_map_t: Dict[str, pd.DataFrame] = {}

    for symbol in symbols:
        stock_name = stock_names.get(symbol, symbol)

        try:
            pre_start_swing = start_date - timedelta(days=warmup_days_swing)
            df_swing = provider.get_data(
                symbol,
                period=swing_period,
                start_date=pre_start_swing,
                end_date=end_date,
            )

            pre_start_t = start_date - timedelta(days=warmup_days_t)
            df_t = provider.get_data(
                symbol, period=t_period, start_date=pre_start_t, end_date=end_date
            )

            df_swing = _normalize_daily_index(df_swing)

            if df_swing is None or df_swing.empty or df_t is None or df_t.empty:
                logger.warning(f"{stock_name} ({symbol}) 多周期数据为空")
                continue

            data_map_swing[symbol] = df_swing
            data_map_t[symbol] = df_t.sort_index()

            logger.info(
                f"已加载 {stock_name} ({symbol}): 日K={len(df_swing)} 条, {t_timeframe}={len(df_t)} 条"
            )

        except Exception as e:
            logger.error(f"加载 {symbol} 多周期数据出错: {e}")

    if not data_map_swing:
        logger.error("没有可用的多周期回测数据。")
        return {}

    engine = _create_engine(quote_ctx, strategy, symbols)

    results = _run_multi_timeframe_simulation(
        engine, data_map_swing, data_map_t, start_date, end_date
    )

    initial_balance = float(cfg.get("backtest.initial_balance", 100000.0))
    benchmark_returns = provider.get_benchmark_returns(start_date, end_date)

    print_backtest_summary(
        results, start_date, end_date, initial_balance, benchmark_returns
    )
    _generate_performance_chart(results, start_date, end_date)

    return results


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
    plot_config = cfg.get("plot", {})
    if not plot_config.get("enabled", False):
        return

    logger.info("正在生成收益率图表...")

    # 获取基准数据
    benchmarks_data = {}
    benchmarks_config = plot_config.get("benchmarks", [])

    if not benchmarks_config:
        backtest_benchmarks = cfg.get("backtest.benchmarks", [])
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

    try:
        start_time_str = cfg.get("backtest.start_time", "2023-01-01")
        end_time_str = cfg.get("backtest.end_time", "2023-12-31")
        start_date = datetime.strptime(start_time_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_time_str, "%Y-%m-%d").date()

        from app.providers.longport import (
            load_cn_universe_symbols,
            load_hkconnect_universe_symbols,
        )

        universe_items: List[Dict[str, Any]] = []
        universe_items.extend(load_cn_universe_symbols())
        universe_items.extend(load_hkconnect_universe_symbols())

        symbols_universe = sorted(
            {
                cast(str, r.get("symbol") or "")
                for r in universe_items
                if r.get("symbol")
            }
        )
        if not symbols_universe:
            logger.error(
                "Universe symbols are empty. Run run_universe_symbols_refresh() first."
            )
            return {}

        from app.core.setup import get_strategy_config

        strat_config = get_strategy_config()
        period = cast(Period, strat_config["period"])
        warmup_days = _resolve_warmup_days(period)

        selector_cfg = cfg.get("universe.selector", {}) or {}
        max_symbols = int(selector_cfg.get("max_symbols", 5))
        one_per_industry = bool(selector_cfg.get("one_per_industry", True))

        data_cfg = cfg.get("data", {}) or {}
        batch_size = int(data_cfg.get("batch_size", 200))

        refresh_cfg = cfg.get("universe.refresh", {}) or {}
        lookback_days = int(refresh_cfg.get("lookback_days", 120))

        mt_cfg = cfg.get("backtest.multi_timeframe", {}) or {}
        multi_timeframe_enabled = bool(mt_cfg.get("enabled", False))

        if multi_timeframe_enabled:
            # Keep existing behavior for multi-timeframe mode.
            logger.info("Multi-timeframe backtest uses cached pool behavior for now.")
            from app.providers.longport import get_stock_pool

            symbols = get_stock_pool()
            if not symbols:
                logger.error("股票池为空，请先运行universe刷新")
                return {}

            provider = LongPortProvider()
            provider.initialize(quote_ctx=quote_ctx)
            stock_names = provider.get_stock_names(symbols)

            return _run_multi_timeframe_backtest(
                quote_ctx=quote_ctx,
                strategy=strategy,
                symbols=symbols,
                stock_names=stock_names,
                start_date=start_date,
                end_date=end_date,
            )

        # Daily workflow: close-phase build pool, open-phase execute.
        pool_builder = BacktestUniversePoolBuilder(
            quote_ctx=quote_ctx,
            max_symbols=max_symbols,
            one_per_industry=one_per_industry,
            lookback_days=lookback_days,
            batch_size=batch_size,
        )

        # Engine initializes on full universe to keep name/lot size consistent.
        engine = _create_engine(quote_ctx, strategy, symbols_universe)

        workflow = BacktestDailyWorkflow(
            quote_ctx=quote_ctx,
            engine=engine,
            pool_builder=pool_builder,
            symbols_universe=symbols_universe,
            period=period,
            warmup_days=warmup_days,
        )

        results = workflow.run(start_date=start_date, end_date=end_date)

        initial_balance = float(cfg.get("backtest.initial_balance", 100000.0))

        provider = LongPortProvider()
        provider.initialize(quote_ctx=quote_ctx)
        benchmark_returns = provider.get_benchmark_returns(start_date, end_date)

        print_backtest_summary(
            results, start_date, end_date, initial_balance, benchmark_returns
        )
        _generate_performance_chart(results, start_date, end_date)

        return results

    except Exception as e:
        logger.error(str(e))
        return {}
