# TradeFlow 项目 AI 文档

本文档由脚本自动生成，旨在帮助 AI 理解项目结构和代码逻辑。

## 文件: `app/main.py`

### 类

#### `class LongportCredentials`

#### `class AppBootstrap`

**方法:**

- `__init__(self) -> None`
- `create_quote_context(self) -> Optional[QuoteContext]`
- `create_strategy(self) -> None`
- `_load_credentials(self) -> Optional[LongportCredentials]`

#### `class TradingWorkflow`

**方法:**

- `__init__(self, quote_ctx) -> None`
- `run(self) -> None`
- `_is_universe_refresh_enabled() -> bool`
- `_is_backtest_enabled() -> bool`
- `_run_close_market_refresh(self) -> None`
- `_run_backtest(self) -> None`
- `_run_live_trading(self) -> None`

### 函数

#### `def main() -> None`

Application entrypoint.

---

## 文件: `app/core/config.py`

### 类

#### `class Timeframe(str, Enum)`

时间周期枚举

#### `class MarketType(str, Enum)`

市场类型枚举

#### `class StrategyMode(str, Enum)`

策略模式枚举

#### `class CompositeMode(str, Enum)`

组合策略模式枚举

#### `class LongPortConfig(BaseModel)`

长桥API配置

**方法:**

- `validate_not_empty(cls, v) -> None`

#### `class LogConfig(BaseModel)`

日志配置

**方法:**

- `validate_log_level(cls, v) -> None`

#### `class EmailConfig(BaseModel)`

邮件通知配置

**方法:**

- `validate_port(cls, v) -> None`

#### `class PositionSizingConfig(BaseModel)`

仓位管理配置

#### `class TradingConfig(BaseModel)`

交易配置

#### `class StrategyParams(BaseModel)`

策略参数配置

#### `class StrategyConfig(BaseModel)`

策略配置

**方法:**

- `validate_composite_mode(cls, v, values) -> None`

#### `class BacktestConfig(BaseModel)`

回测配置

**方法:**

- `validate_date_format(cls, v) -> None`

#### `class UniverseConfig(BaseModel)`

标的配置

#### `class AppConfig(BaseModel)`

应用程序配置

#### `class ConfigManager`

配置管理器，提供统一的配置加载、验证和管理功能。

**方法:**

- `__init__(self, config_path) -> None`
- `_get_default_config_path(self) -> str`
  - 获取默认配置文件路径
- `load(self) -> bool`
  - 加载并验证配置
- `_load_raw_config(self) -> Dict[Any]`
  - 加载原始配置数据
- `_apply_env_overrides(self, config) -> Dict[Any]`
  - 应用环境变量覆盖
- `get(self, key, default) -> Any`
  - 使用点号表示法获取配置值。
- `get_validated(self, key, default) -> Any`
  - 获取经过验证的配置值。
- `validate(self) -> bool`
  - 验证配置的有效性
- `get_config_summary(self) -> Dict[Any]`
  - 获取配置摘要信息
- `reload(self) -> bool`
  - 重新加载配置

### 函数

#### `def get_config() -> ConfigManager`

获取全局配置管理器

#### `def load_config(config_path) -> bool`

加载配置

#### `def get_config_value(key, default) -> Any`

获取配置值（向后兼容）

#### `def get_validated_config_value(key, default) -> Any`

获取验证后的配置值

#### `def validate_config() -> bool`

验证配置

#### `def get_config_summary() -> Dict[Any]`

获取配置摘要

---

## 文件: `app/core/constants.py`

### 类

#### `class SignalType(str, Enum)`

交易信号类型枚举

#### `class MarketBoard(str, Enum)`

市场板块枚举

---

## 文件: `app/core/logger.py`

### 类

#### `class CustomFormatter`

自定义日志格式化器，根据日志级别更改格式。

DEBUG 级别包含时间戳、模块名、级别和消息。
其他级别仅包含消息。

**方法:**

- `__init__(self) -> None`
- `format(self, record) -> str`

### 函数

#### `def _archive_old_logs(log_path) -> None`

启动时归档现有的日志文件。

Args:
    log_path: 当前日志文件的路径。

#### `def _cleanup_old_backups(log_path, backup_count) -> None`

清理旧的启动日志备份。

Args:
    log_path: 日志文件路径（备份的基础）。
    backup_count: 保留的备份数量。

#### `def setup_logging(config) -> None`

初始化日志配置。

Args:
    config: 包含 'log' 设置的配置字典。

---

## 文件: `app/core/setup.py`

### 函数

#### `def initialize_trading_context(quote_ctx) -> Tuple[Any]`

初始化交易上下文：获取股票池和股票名称。

#### `def get_strategy_config() -> Dict[Any]`

获取策略相关的通用配置。

---

## 文件: `app/strategies/macd.py`

### 类

#### `class MACDStrategy(Strategy)`

移动平均收敛散度 (MACD) 策略。

**方法:**

- `__init__(self, fast, slow, signal) -> None`
  - 初始化 MACD 策略。
- `_on_initialize(self) -> bool`
  - MACD策略初始化
- `analyze(self, symbol, df) -> Dict[Any]`
  - 使用 MACD 策略分析数据。
- `get_info(self) -> Dict[Any]`
  - 获取MACD策略的详细信息

---

## 文件: `app/strategies/composite.py`

### 类

#### `class CompositeStrategy(Strategy)`

组合策略，结合多个子策略。

**方法:**

- `__init__(self, strategies, mode, name, description) -> None`
  - 初始化组合策略。
- `_on_initialize(self) -> bool`
  - 组合策略初始化
- `analyze(self, symbol, df) -> Dict[Any]`
  - 使用多个策略分析数据并合并结果。
- `add_strategy(self, strategy) -> None`
  - 添加子策略到组合中。
- `remove_strategy(self, strategy_name) -> bool`
  - 从组合中移除指定名称的子策略。
- `get_info(self) -> Dict[Any]`
  - 获取组合策略的详细信息
- `_on_cleanup(self) -> None`
  - 清理所有子策略资源

---

## 文件: `app/strategies/rsi.py`

### 类

#### `class RSIStrategy(Strategy)`

相对强弱指数 (RSI) 策略。

**方法:**

- `__init__(self, period, overbought, oversold) -> None`
  - 初始化 RSI 策略。
- `_on_initialize(self) -> bool`
  - RSI策略初始化
- `analyze(self, symbol, df) -> Dict[Any]`
  - 使用 RSI 策略分析数据。
- `get_info(self) -> Dict[Any]`
  - 获取RSI策略的详细信息

---

## 文件: `app/strategies/manager.py`

### 类

#### `class StrategyConfig`

策略配置类，封装策略参数和配置

**方法:**

- `__init__(self, name, params, description) -> None`
- `validate(self) -> bool`
  - 验证配置参数的有效性
- `__str__(self) -> str`

#### `class StrategyRegistry`

策略注册表，管理所有可用的策略

**方法:**

- `__init__(self) -> None`
- `register(self, name, strategy_class, default_params, description) -> None`
  - 注册策略
- `_extract_param_types(self, strategy_class) -> Dict[Any]`
  - 提取策略构造函数的参数类型信息
- `get_strategy_class(self, name) -> Optional[Type[Strategy]]`
  - 获取策略类
- `get_available_strategies(self) -> List[str]`
  - 获取所有可用的策略名称
- `get_strategy_config(self, name) -> Optional[Dict[Any]]`
  - 获取策略配置信息
- `validate_config(self, config) -> bool`
  - 验证策略配置

#### `class StrategyManager`

策略管理器，负责策略的创建、配置和执行

**方法:**

- `__init__(self) -> None`
- `register_strategy(self, name, strategy_class, default_params, description) -> None`
  - Register a strategy into this manager's registry.
- `initialize(self) -> None`
  - 初始化策略管理器，注册所有内置策略
- `create_strategy(self, config) -> Optional[Strategy]`
  - 根据配置创建策略实例
- `create_strategy_from_dict(self, strategy_config) -> Optional[Strategy]`
  - 从字典配置创建策略
- `get_strategy(self, strategy_id) -> Optional[Strategy]`
  - 获取策略实例
- `remove_strategy(self, strategy_id) -> bool`
  - 移除策略实例
- `get_active_strategies(self) -> Dict[Any]`
  - 获取所有活跃的策略实例
- `analyze_with_strategy(self, strategy_id, symbol, df) -> Optional[Dict[Any]]`
  - 使用指定策略分析数据

### 函数

#### `def register_strategy(name, strategy_class, default_params, description) -> None`

全局函数：注册策略

#### `def get_strategy_manager() -> StrategyManager`

获取全局策略管理器

---

## 文件: `app/strategies/base.py`

### 类

#### `class Strategy(ABC)`

所有交易策略的抽象基类。
提供统一的策略接口和生命周期管理。

**方法:**

- `__init__(self, name, description) -> None`
  - 初始化策略。
- `initialize(self) -> bool`
  - 初始化策略，在第一次分析前调用。
- `_on_initialize(self) -> bool`
  - 子类可以重写的初始化钩子方法。
- `analyze(self, symbol, df) -> Dict[Any]`
  - 分析市场数据并生成交易信号。
- `analyze_with_initialization(self, symbol, df) -> Dict[Any]`
  - 带初始化的分析方法，确保策略在使用前已初始化。
- `get_info(self) -> Dict[Any]`
  - 获取策略信息。
- `validate_data(self, df, required_columns) -> bool`
  - 验证输入数据的有效性。
- `cleanup(self) -> None`
  - 清理策略资源，在策略不再使用时调用。
- `_on_cleanup(self) -> None`
  - 子类可以重写的清理钩子方法。
- `__str__(self) -> str`
  - 返回策略的字符串表示
- `__repr__(self) -> str`
  - 返回策略的详细表示

---

## 文件: `app/strategies/trend_swing_t.py`

### 类

#### `class TrendSwingConfig`

偏波段的趋势突破策略参数。

说明：默认值仅作为兜底，建议在 `config/config.yaml` 的
`strategy.params` 下配置，便于回测与实盘保持一致。

#### `class TrendSwingTStrategy(Strategy)`

趋势突破 + ATR 风控 + 目标仓位管理 + 低频做T（可选）。

**方法:**

- `__init__(self, config) -> None`
- `_on_initialize(self) -> bool`
  - 趋势摆动策略初始化
- `analyze(self, symbol, df) -> Dict[Any]`
  - 分析市场数据并生成交易信号
- `_reset_symbol(self, symbol) -> None`
  - 重置指定标的的状态
- `get_info(self) -> Dict[Any]`
  - 获取趋势摆动策略的详细信息
- `_on_cleanup(self) -> None`
  - 清理策略资源

### 函数

#### `def _calculate_rsi_fast(df, period, column) -> Any`

---

## 文件: `app/utils/finance.py`

### 函数

#### `def calculate_interval_return(start_price, end_price) -> float`

计算区间收益率。

Args:
    start_price: 起始价格
    end_price: 结束价格

Returns:
    float: 收益率百分比，如果起始价格 <= 0 则返回 0.0

#### `def get_price_range(df) -> tuple[Any]`

从 DataFrame 获取起止价格。
假设 DataFrame 包含 'open' 和 'close' 列，且按时间排序。

Returns:
    tuple[float, float]: (start_price, end_price)

---

## 文件: `app/utils/notifier.py`

### 类

#### `class EmailNotifier`

邮件通知处理程序。
使用 SMTP 配置发送邮件。

**方法:**

- `__init__(self) -> None`
  - 使用环境变量或配置文件初始化 EmailNotifier。
- `send_message(self, title, content) -> None`
  - 发送邮件通知。

---

## 文件: `app/utils/indicators.py`

### 函数

#### `def calculate_sma(df, period, column, out_col) -> Any`

计算简单移动平均（SMA）。

#### `def calculate_ema(df, period, column, out_col) -> Any`

计算指数移动平均（EMA）。

#### `def calculate_atr(df, period, out_col) -> Any`

计算平均真实波幅（ATR）。要求 df 至少包含 high/low/close。

#### `def calculate_donchian_channel(df, period, high_col, low_col, out_high, out_low, out_mid) -> Any`

计算 Donchian 通道（常用于趋势突破策略）。

#### `def calculate_adx(df, period, out_adx, out_plus_di, out_minus_di) -> Any`

计算 ADX（趋势强度）。要求 df 至少包含 high/low/close。

#### `def calculate_macd(df, fast, slow, signal, column) -> Any`

计算 MACD 指标。

Args:
    df: 包含价格数据的 DataFrame。
    fast: 快速 EMA 周期。
    slow: 慢速 EMA 周期。
    signal: 信号线 EMA 周期。
    column: 用于计算的价格列名。

Returns:
    添加了 'dif', 'dea', 和 'macd' 列的 DataFrame。

#### `def calculate_rsi(df, period, column) -> Any`

计算 RSI 指标。

Args:
    df: 包含价格数据的 DataFrame。
    period: RSI 计算周期。
    column: 用于计算的价格列名。

Returns:
    添加了 'rsi' 列的 DataFrame。

#### `def calculate_bollinger_bands(df, period, std_dev, column) -> Any`

计算布林带指标。

Args:
    df: 包含价格数据的 DataFrame。
    period: 移动平均周期。
    std_dev: 标准差倍数。
    column: 用于计算的价格列名。

Returns:
    添加了 'upper', 'middle', 'lower' 列的 DataFrame。

---

## 文件: `app/utils/formatting.py`

### 函数

#### `def get_display_width(s) -> int`

计算字符串的显示宽度（东亚宽度）。

#### `def pad_string(s, width, align) -> str`

用空格填充字符串以达到目标显示宽度。
align: '<' 左对齐 (默认), '>' 右对齐

---

## 文件: `app/utils/plotter.py`

### 函数

#### `def create_performance_chart(equity_curve, trades, benchmark_data, config, output_dir, filename) -> str`

创建账户收益率与基准对比的交互式图表。

Args:
    equity_curve: 账户权益曲线列表，每项包含 'time' 和 'equity'。
    trades: 交易记录列表。
    benchmark_data: 基准数据字典，键为 symbol，值为包含 'close' 的 DataFrame。
    config: 绘图配置字典。
    output_dir: 输出目录。
    filename: 输出文件名。

Returns:
    生成的 HTML 文件路径。

---

## 文件: `app/utils/reporting.py`

### 函数

#### `def print_backtest_summary(results, start_date, end_date, initial_balance, benchmark_returns) -> None`

打印回测摘要表格。

Args:
    results: 回测结果字典。
    start_date: 回测开始日期。
    end_date: 回测结束日期。
    initial_balance: 初始资金。
    benchmark_returns: 基准收益字典。

---

## 文件: `app/runners/universe_refresh.py`

### 类

#### `class UniverseSymbolProvider(Protocol)`

**方法:**

- `get_universe_symbols(self, market) -> List[Dict[Any]]`

#### `class ExchangeUniverseSymbolProvider`

**方法:**

- `__init__(self) -> None`
- `get_universe_symbols(self, market) -> List[Dict[Any]]`

#### `class UniverseScorer(Protocol)`

**方法:**

- `score(self, symbol, candles, fundamentals) -> float`

#### `class TechnicalMomentumScorer`

Simple momentum score by 5-day price change.

**方法:**

- `score(self, symbol, candles, fundamentals) -> float`

#### `class VolatilityHotnessScorer`

Simple hotness score by 20-day volatility.

**方法:**

- `score(self, symbol, candles, fundamentals) -> float`

#### `class PlaceholderNewsScorer`

**方法:**

- `score(self, symbol, candles, fundamentals) -> float`

#### `class FundamentalQualityScorer`

**方法:**

- `score(self, symbol, candles, fundamentals) -> float`
- `_to_float(value) -> float`

#### `class UniverseScoringWeights`

**方法:**

- `from_config(cls) -> UniverseScoringWeights`

#### `class UniverseCompositeScorer`

**方法:**

- `__init__(self, weights, technical, sentiment, news, fundamental) -> None`
- `score(self, symbol, candles, fundamentals) -> Dict[Any]`

#### `class UniverseCandidateSelector`

**方法:**

- `__init__(self, max_symbols, one_per_industry) -> None`
- `select(self, candidates) -> List[str]`

#### `class UniverseRefreshService`

**方法:**

- `__init__(self, symbol_provider) -> None`
- `refresh_symbols(self, markets) -> List[Dict[Any]]`

#### `class UniverseScoringService`

**方法:**

- `__init__(self, composite_scorer) -> None`
- `build_candidates(self, quote_ctx, symbols, name_map, industry_map, board_map, fundamentals_map, lookback_days, batch_size) -> List[Dict[Any]]`

### 函数

#### `def run_universe_symbols_refresh() -> None`

Step 1: refresh universe symbol list without relying on Longbridge API.

#### `def run_universe_refresh(quote_ctx) -> None`

Step 2: load universe list, fetch data from Longbridge, and score candidates.

---

## 文件: `app/runners/engine.py`

### 类

#### `class MarketDataSource(ABC)`

Market data source abstraction for engine runs.

**方法:**

- `iter_signal_points(self) -> Iterable[tuple[Any]]`
  - Yield (symbol, signal_time, slice_df) for analysis.
- `get_latest_price(self, symbol, signal_time) -> float`

#### `class BacktestDataSource(MarketDataSource)`

**方法:**

- `__init__(self, data, start_time) -> None`
- `iter_signal_points(self) -> Iterable[tuple[Any]]`
- `get_latest_price(self, symbol, signal_time) -> float`

#### `class LiveDataSource(MarketDataSource)`

**方法:**

- `__init__(self, quote_ctx, symbols, period, history_count, request_delay) -> None`
- `iter_signal_points(self) -> Iterable[tuple[Any]]`
- `get_latest_price(self, symbol, signal_time) -> float`

#### `class ExecutionEngine(ABC)`

策略执行引擎抽象基类，定义统一的策略执行接口。

**方法:**

- `__init__(self, strategy, position_manager, initial_capital, commission_rate, position_ratio) -> None`
- `initialize(self, symbols, quote_ctx) -> bool`
  - 初始化执行引擎
- `_allow_t_trade(self, symbol, current_time) -> bool`
  - 做T频控：仅限制 trade_tag=="T" 的信号。
- `_mark_t_trade(self, symbol, current_time) -> None`
  - 标记做T交易
- `process_signal(self, symbol, signal, current_time, current_price) -> Dict[Any]`
  - 处理单个信号
- `record_equity(self, timestamp) -> None`
  - 记录当前权益
- `get_performance(self) -> Dict[Any]`
  - 获取性能指标
- `get_results(self) -> Dict[Any]`
  - 获取完整结果
- `run(self) -> Dict[Any]`
  - 运行策略执行引擎
- `cleanup(self) -> None`
  - 清理资源

#### `class BacktestEngine(ExecutionEngine)`

回测执行引擎

**方法:**

- `__init__(self) -> None`
- `set_data(self, data) -> None`
  - 设置回测数据
- `run(self, start_time) -> Dict[Any]`
  - 运行回测

#### `class LiveEngine(ExecutionEngine)`

实盘执行引擎

**方法:**

- `__init__(self) -> None`
- `set_live_params(self, quote_ctx, symbols, period, history_count, interval, request_delay) -> None`
  - 设置实盘参数
- `run(self) -> Dict[Any]`
  - 运行实盘监控
- `_is_stale(self, signal_time) -> bool`
- `_get_period_seconds(self, period) -> int`
  - 获取时间周期对应的秒数
- `_send_notification(self, symbol, stock_name, signal, signal_time, current_price, result) -> None`
  - 发送交易通知

#### `class EngineFactory`

执行引擎工厂类

**方法:**

- `create_backtest_engine(strategy, position_manager, initial_capital, commission_rate, position_ratio) -> BacktestEngine`
  - 创建回测引擎
- `create_live_engine(strategy, position_manager, initial_capital, commission_rate, position_ratio) -> LiveEngine`
  - 创建实盘引擎

---

## 文件: `app/runners/live.py`

### 类

#### `class LiveTradingConfig`

**方法:**

- `from_global_config(cls) -> LiveTradingConfig`

#### `class LiveTradingService`

**方法:**

- `__init__(self, quote_ctx, strategy, config) -> None`
- `run(self) -> Dict[Any]`
- `_load_account_state(engine) -> None`
- `_save_account_state(engine) -> None`

### 函数

#### `def run_live_trading(quote_ctx, strategy) -> Dict[Any]`

执行实盘交易监控（Runner entrypoint）。

---

## 文件: `app/runners/backtest.py`

### 类

#### `class BacktestConfig`

**方法:**

- `from_global_config(cls) -> BacktestConfig`

#### `class BacktestUniversePoolBuilder`

**方法:**

- `__init__(self, quote_ctx, max_symbols, one_per_industry, lookback_days, batch_size) -> None`
- `build_pool(self, all_symbols, as_of) -> List[str]`

#### `class BacktestDailyWorkflow`

**方法:**

- `__init__(self, quote_ctx, engine, pool_builder, symbols_universe, period, warmup_days) -> None`
- `run(self, start_date, end_date) -> Dict[Any]`
- `_load_day_data(self, symbols, day, start_date, end_date) -> Dict[Any]`

#### `class BacktestService`

**方法:**

- `__init__(self, quote_ctx, strategy, config) -> None`
- `run(self) -> Dict[Any]`
- `_parse_date_range(self) -> tuple[Any]`
- `_resolve_warmup_days(self, period) -> int`
- `_run_single_timeframe_backtest(self, symbols, stock_names, lot_sizes, start_date, end_date, warmup_days, period) -> Dict[Any]`
- `_run_multi_timeframe_backtest(self, symbols, stock_names, lot_sizes, start_date, end_date) -> Dict[Any]`
- `_create_engine(self, symbols) -> BacktestEngine`

### 函数

#### `def _normalize_daily_index(df) -> Any`

将日K索引规范到日期 00:00:00，避免与 15m 索引对齐时产生歧义。

#### `def _get_day_range(day) -> tuple[Any]`

获取指定日期的开始和结束时间

#### `def _run_multi_timeframe_simulation(engine, data_map_swing, data_map_t, start_date, end_date) -> Dict[Any]`

运行多周期模拟

#### `def _generate_performance_chart(results, start_date, end_date) -> None`

生成性能图表

#### `def run_backtest(quote_ctx, strategy) -> Dict[Any]`

执行回测流程（Runner entrypoint）。

---

## 文件: `app/data/provider.py`

### 函数

#### `def initialize_data_providers(quote_ctx) -> bool`

初始化所有数据提供器

#### `def _load_json(path, default) -> Any`

加载JSON文件

#### `def _save_json(path, data) -> None`

保存JSON文件

#### `def save_universe_symbols(path, items) -> None`

保存标的基础清单（代码+名称）。

#### `def load_universe_symbols(path) -> List[Dict[Any]]`

加载标的基础清单

#### `def save_cn_universe_symbols(items) -> None`

保存A股标的清单

#### `def load_cn_universe_symbols() -> List[Dict[Any]]`

加载A股标的清单

#### `def save_hkconnect_universe_symbols(items) -> None`

保存港股通标的清单

#### `def load_hkconnect_universe_symbols() -> List[Dict[Any]]`

加载港股通标的清单

#### `def get_universe_symbols_paths() -> Dict[Any]`

获取标的清单文件路径

#### `def _select_top_symbols(candidates, max_symbols, one_per_industry) -> List[str]`

选择顶级标的

#### `def get_stock_pool() -> List[str]`

获取需要监控的股票代码列表。

#### `def refresh_universe_cache(snapshot, scores) -> None`

将闭市扫描得到的全市场快照与打分结果写入本地缓存。

#### `def get_stock_names(quote_ctx, symbols) -> Dict[Any]`

获取指定股票代码的股票名称。

#### `def get_stock_lot_sizes(quote_ctx, symbols) -> Dict[Any]`

获取指定股票代码的最小交易单位（lot size）。

#### `def get_period(timeframe_str) -> Period`

将时间周期字符串转换为 LongPort Period 枚举。

#### `def fetch_candles(quote_ctx, symbol, period, count) -> Any`

获取K线数据并转换为 DataFrame。

#### `def get_benchmark_returns(quote_ctx, start_date, end_date) -> Dict[Any]`

计算特定时间段内的基准收益率。

#### `def fetch_history_candles(quote_ctx, symbol, period, start_date, end_date, warmup_days) -> Any`

获取指定日期范围的历史K线数据，支持预热期。

#### `def get_data_provider_manager() -> DataProviderManager`

获取全局数据提供器管理器

---

## 文件: `app/data/interface.py`

### 类

#### `class DataProvider(ABC)`

数据提供器抽象基类，定义统一的数据访问接口。

**方法:**

- `__init__(self, name, description) -> None`
- `initialize(self) -> bool`
  - 初始化数据提供器
- `get_data(self, symbol) -> Optional[Any]`
  - 获取指定标的的数据
- `get_multiple_data(self, symbols) -> Dict[Any]`
  - 批量获取多个标的的数据
- `get_info(self) -> Dict[Any]`
  - 获取数据提供器信息
- `cleanup(self) -> None`
  - 清理资源

#### `class LongPortDataProvider(DataProvider)`

长桥API数据提供器

**方法:**

- `__init__(self, quote_context) -> None`
- `initialize(self) -> bool`
  - 初始化长桥数据提供器
- `get_data(self, symbol) -> Optional[Any]`
  - 获取单个标的的数据
- `get_multiple_data(self, symbols) -> Dict[Any]`
  - 批量获取多个标的的数据
- `_get_realtime_candles(self, symbol, period, count) -> Optional[Any]`
  - 获取实时K线数据
- `_get_history_candles(self, symbol, period, start_date, end_date) -> Optional[Any]`
  - 获取历史K线数据
- `_process_candlesticks(self, candlesticks) -> Any`
  - 处理K线数据并转换为DataFrame

#### `class ExchangeDataProvider(DataProvider)`

交易所官方接口数据提供器

**方法:**

- `__init__(self) -> None`
- `initialize(self) -> bool`
  - 初始化交易所数据提供器
- `get_data(self, symbol) -> Optional[Any]`
  - 获取交易所数据（暂不支持单个标的查询）
- `get_multiple_data(self, symbols) -> Dict[Any]`
  - 批量获取交易所数据（暂不支持）
- `get_universe_symbols(self, market) -> List[Dict[Any]]`
  - 获取指定市场的标的清单
- `_get_cn_universe_symbols(self) -> List[Dict[Any]]`
  - 获取A股标的清单
- `_get_hkconnect_universe_symbols(self) -> List[Dict[Any]]`
  - 获取港股通标的清单

#### `class DataProviderManager`

数据提供器管理器

**方法:**

- `__init__(self) -> None`
- `register_provider(self, name, provider) -> None`
  - 注册数据提供器
- `set_default_provider(self, name) -> bool`
  - 设置默认数据提供器
- `get_provider(self, name) -> Optional[DataProvider]`
  - 获取数据提供器
- `get_data(self, symbol, provider_name) -> Optional[Any]`
  - 通过指定提供器获取数据
- `get_multiple_data(self, symbols, provider_name) -> Dict[Any]`
  - 批量获取数据
- `get_available_providers(self) -> List[str]`
  - 获取所有可用的数据提供器名称
- `initialize_all(self) -> bool`
  - 初始化所有数据提供器

### 函数

#### `def register_data_provider(name, provider) -> None`

全局函数：注册数据提供器

#### `def get_data_provider_manager() -> DataProviderManager`

获取全局数据提供器管理器

---

## 文件: `app/trading/persistence.py`

### 类

#### `class AccountPersistence`

负责 PaperAccount 的持久化（加载和保存）。

**方法:**

- `__init__(self, file_path) -> None`
- `load(self, account) -> bool`
  - 从文件加载账户状态到 account 对象中。
- `save(self, account) -> None`
  - 将 account 对象的状态保存到文件。

---

## 文件: `app/trading/actions.py`

### 类

#### `class TradeActionContext`

#### `class TradeActionHandler(ABC)`

**方法:**

- `can_handle(self, action) -> bool`
- `execute(self, manager, ctx) -> Dict[Any]`

#### `class BuyActionHandler(TradeActionHandler)`

**方法:**

- `can_handle(self, action) -> bool`
- `execute(self, manager, ctx) -> Dict[Any]`

#### `class SellActionHandler(TradeActionHandler)`

**方法:**

- `can_handle(self, action) -> bool`
- `execute(self, manager, ctx) -> Dict[Any]`

#### `class DefaultNoopActionHandler(TradeActionHandler)`

**方法:**

- `can_handle(self, action) -> bool`
- `execute(self, manager, ctx) -> Dict[Any]`

#### `class TradeActionRegistry`

**方法:**

- `__init__(self) -> None`
- `dispatch(self, manager, ctx, action) -> Dict[Any]`

---

## 文件: `app/trading/position.py`

### 类

#### `class PositionSizingConfig`

仓位管理参数（风险预算 + 再平衡 + 低频交易）。

#### `class PositionManager`

管理仓位规模、资金分配与再平衡。

**方法:**

- `__init__(self, position_ratio, config) -> None`
- `_normalize_quantity(self, quantity, lot_size) -> int`
- `calculate_target_position_ratio(self, signal) -> float`
  - 根据策略因子计算目标仓位比例。
- `calculate_order_quantity(self, action, current_position, price, total_equity, available_cash, lot_size, signal) -> int`
  - 把 BUY/SELL 信号转换为具体下单数量（支持加/减仓）。
- `get_position_suggestion(self, signal, current_price, total_capital) -> str`

---

## 文件: `app/trading/manager.py`

### 类

#### `class TradeManager`

统一交易管理器，负责协调账户管理、仓位管理和交易执行。
简化职责边界：
- Account: 只负责资金和持仓的存储、计算
- PositionManager: 只负责仓位计算和风险控制
- TradeManager: 统一协调交易流程和信号处理

**方法:**

- `__init__(self, account, position_manager, lot_sizes) -> None`
- `set_lot_sizes(self, lot_sizes) -> None`
  - 设置股票最小交易单位
- `execute_trade(self, signal, symbol, timestamp, price) -> Dict[Any]`
  - 执行交易信号，统一处理买入和卖出逻辑。
- `_execute_buy(self, signal_id, symbol, timestamp, price, reason, factors, trade_tag) -> Dict[Any]`
  - 执行买入交易
- `_execute_sell(self, signal_id, symbol, timestamp, price, reason, factors, trade_tag) -> Dict[Any]`
  - 执行卖出交易
- `_normalize_quantity(self, symbol, quantity) -> int`
  - 数量标准化（按最小交易单位）
- `get_trade_stats(self) -> Dict[Any]`
  - 获取交易统计信息
- `get_account_info(self) -> Dict[Any]`
  - 获取账户信息
- `get_position_suggestion(self, signal, current_price, total_equity) -> str`
  - 获取仓位建议
- `clear_processed_signals(self) -> None`
  - 清空已处理的信号记录
- `get_processed_signals_count(self) -> int`
  - 获取已处理信号数量

#### `class TradeManagerFactory`

交易管理器工厂类

**方法:**

- `create_trade_manager(initial_capital, commission_rate, position_ratio, lot_sizes) -> TradeManager`
  - 创建交易管理器
- `create_trade_manager_from_account(account, position_manager, lot_sizes) -> TradeManager`
  - 从现有账户创建交易管理器

---

## 文件: `app/trading/executor.py`

### 类

#### `class TradeExecutor`

交易执行器（简化版），作为TradeManager的适配器层。
主要职责：
- 适配新老接口，保持向后兼容
- 提供简单的execute方法
- 处理信号ID重复检查

**方法:**

- `__init__(self, trade_manager) -> None`
- `execute(self, signal, symbol, time, price) -> Dict[Any]`
  - 执行交易信号（适配器方法，保持向后兼容）。
- `set_lot_sizes(self, lot_sizes) -> None`
  - 设置股票最小交易单位
- `account(self) -> None`
  - 获取账户对象（向后兼容）
- `position_manager(self) -> None`
  - 获取仓位管理器（向后兼容）

#### `class LegacyTradeExecutor`

旧版交易执行器（已弃用），用于向后兼容。
新代码应使用TradeManager。

**方法:**

- `__init__(self, account, position_manager) -> None`
- `set_lot_sizes(self, lot_sizes) -> None`
  - 设置股票最小交易单位
- `execute(self, signal, symbol, time, price) -> Dict[Any]`
  - 执行交易信号（旧版实现，仅用于兼容）。

### 函数

#### `def create_trade_executor(account, position_manager, trade_manager) -> TradeExecutor`

创建交易执行器工厂函数。

Args:
    account: 账户对象（旧版方式）
    position_manager: 仓位管理器（旧版方式）
    trade_manager: 交易管理器（新版方式）
    **kwargs: 其他参数
    
Returns:
    交易执行器实例

---

## 文件: `app/trading/account.py`

### 类

#### `class PaperAccount`

模拟交易账户，专注于资金和持仓管理。

职责边界：
- 管理现金余额和持仓
- 计算权益和收益
- 记录交易历史
- 不包含交易决策逻辑

**方法:**

- `__init__(self, initial_capital, commission_rate, on_trade) -> None`
- `set_stock_names(self, names) -> None`
  - 设置股票名称映射
- `update_price(self, symbol, price) -> None`
  - 更新股票最新价格
- `get_total_equity(self) -> float`
  - 计算当前总权益（现金 + 持仓市值）
- `get_position_value(self, symbol) -> float`
  - 获取指定股票的持仓市值
- `get_position_ratio(self, symbol) -> float`
  - 获取指定股票的仓位比例
- `record_equity(self, timestamp, equity) -> None`
  - 记录当前权益。
- `get_trade_stats(self) -> Dict[Any]`
  - 计算交易统计信息，包括胜率等。
- `buy(self, symbol, price, quantity, time, reason, signal_id, factors, trade_tag) -> bool`
  - 执行买入操作（纯资金和持仓管理）。
- `sell(self, symbol, price, quantity, time, reason, signal_id, factors, trade_tag) -> bool`
  - 执行卖出操作（纯资金和持仓管理）。
- `_record_trade(self, action, symbol, price, quantity, time, reason, signal_id, factors, trade_tag, position_before, position_after, commission, profit_ratio) -> None`
  - 记录交易详情
- `clear_trades(self) -> None`
  - 清空交易记录
- `get_account_summary(self) -> Dict[Any]`
  - 获取账户摘要信息
- `is_signal_processed(self, signal_id) -> bool`
  - 检查信号是否已处理
- `mark_signal_processed(self, signal_id) -> None`
  - 标记信号为已处理
- `clear_processed_signals(self) -> None`
  - 清空已处理的信号记录

---

