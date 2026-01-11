# TradeFlow 项目 AI 文档

本文档由脚本自动生成，旨在帮助 AI 理解项目结构和代码逻辑。

## 文件: `app\main.py`

### 函数

#### `def main() -> None`

主入口点。

---

## 文件: `app\core\config.py`

### 类

#### `class AppConfig`

应用程序配置管理器。
从 YAML 文件加载配置并提供访问方法。

**方法:**

- `__init__(self, config_path) -> None`
  - 初始化 AppConfig。
- `_load_config(self, path) -> Dict[Any]`
  - 从 YAML 文件加载配置。
- `get(self, key, default) -> Any`
  - 使用点号表示法获取配置值。

---

## 文件: `app\core\constants.py`

### 类

#### `class SignalType(str, Enum)`

交易信号类型枚举

---

## 文件: `app\core\logger.py`

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

## 文件: `app\core\setup.py`

### 函数

#### `def initialize_trading_context(quote_ctx) -> Tuple[Any]`

初始化交易上下文：获取股票池和股票名称。

#### `def get_strategy_config() -> Dict[Any]`

获取策略相关的通用配置。

---

## 文件: `app\data\provider.py`

### 函数

#### `def get_stock_pool() -> List[str]`

获取需要监控的股票代码列表。

#### `def get_stock_names(quote_ctx, symbols) -> Dict[Any]`

获取指定股票代码的股票名称。

Args:
    quote_ctx: LongPort QuoteContext 对象。
    symbols: 股票代码列表。

Returns:
    股票代码到股票名称的映射字典。

#### `def get_stock_lot_sizes(quote_ctx, symbols) -> Dict[Any]`

获取指定股票代码的最小交易单位（lot size）。

Args:
    quote_ctx: LongPort QuoteContext 对象。
    symbols: 股票代码列表。

Returns:
    股票代码到最小交易单位的映射字典。默认为 1。

#### `def get_period(timeframe_str) -> Period`

将时间周期字符串转换为 LongPort Period 枚举。

#### `def _process_candlesticks(candlesticks) -> Any`

处理 K 线数据列表并转换为 DataFrame。

Args:
    candlesticks: LongPort K 线对象列表。
    
Returns:
    包含 'time', 'open', 'high', 'low', 'close', 'volume' 的 DataFrame。

#### `def fetch_candles(quote_ctx, symbol, period, count) -> Any`

获取K线数据并转换为 DataFrame。

Args:
    quote_ctx: LongPort QuoteContext 对象。
    symbol: 股票代码。
    period: K线周期。
    count: 获取的K线数量。

Returns:
    包含 'time', 'open', 'high', 'low', 'close', 'volume' 的 DataFrame。

#### `def get_benchmark_returns(quote_ctx, start_date, end_date) -> Dict[Any]`

计算特定时间段内的基准收益率。

#### `def fetch_history_candles(quote_ctx, symbol, period, start_date, end_date, warmup_days) -> Any`

获取指定日期范围的历史K线数据，支持预热期。

Args:
    quote_ctx: LongPort QuoteContext 对象。
    symbol: 股票代码。
    period: K线周期。
    start_date: 开始日期。
    end_date: 结束日期。
    warmup_days: 预热天数，将在 start_date 之前获取额外的数据。

Returns:
    包含历史数据的 DataFrame。

---

## 文件: `app\runners\backtest.py`

### 类

#### `class BacktestEngine`

事件驱动的回测引擎。
基于策略信号模拟交易执行。

**方法:**

- `__init__(self, strategy, initial_capital, commission_rate, position_ratio) -> None`
- `set_stock_names(self, names) -> None`
  - 设置股票名称映射
- `set_lot_sizes(self, lot_sizes) -> None`
  - 设置股票最小交易单位
- `_allow_t_trade(self, symbol, current_time) -> bool`
  - 做T频控：仅限制 trade_tag=="T" 的信号。
- `_mark_t_trade(self, symbol, current_time) -> None`
- `run(self, data, start_time) -> None`
  - 运行回测模拟（支持多股票）。
- `_calculate_performance(self) -> None`
  - 计算最终性能指标，包括个股收益。
- `_calculate_symbol_performance(self) -> None`
  - 计算并打印个股收益情况
- `get_results(self) -> Dict[Any]`
  - 获取回测结果。

### 函数

#### `def _normalize_daily_index(df) -> Any`

将日K索引规范到日期 00:00:00，避免与 15m 索引对齐时产生歧义。

#### `def _get_day_range(day) -> Tuple[Any]`

#### `def run_backtest(quote_ctx, strategy) -> None`

执行回测流程。

---

## 文件: `app\runners\live.py`

### 函数

#### `def run_live_trading(quote_ctx, strategy, pos_manager) -> None`

执行实盘交易监控循环。

---

## 文件: `app\strategies\base.py`

### 类

#### `class Strategy(ABC)`

所有交易策略的抽象基类。

**方法:**

- `__init__(self) -> None`
- `analyze(self, symbol, df) -> Dict[Any]`
  - 分析市场数据并生成交易信号。

---

## 文件: `app\strategies\composite.py`

### 类

#### `class CompositeStrategy(Strategy)`

组合策略，结合多个子策略。

**方法:**

- `__init__(self, strategies, mode) -> None`
  - 初始化组合策略。
- `analyze(self, symbol, df) -> Dict[Any]`
  - 使用多个策略分析数据并合并结果。

---

## 文件: `app\strategies\macd.py`

### 类

#### `class MACDStrategy(Strategy)`

移动平均收敛散度 (MACD) 策略。

**方法:**

- `__init__(self, fast, slow, signal) -> None`
  - 初始化 MACD 策略。
- `analyze(self, symbol, df) -> Dict[Any]`
  - 使用 MACD 策略分析数据。

---

## 文件: `app\strategies\rsi.py`

### 类

#### `class RSIStrategy(Strategy)`

相对强弱指数 (RSI) 策略。

**方法:**

- `__init__(self, period, overbought, oversold) -> None`
  - 初始化 RSI 策略。
- `analyze(self, symbol, df) -> Dict[Any]`
  - 使用 RSI 策略分析数据。

---

## 文件: `app\strategies\trend_swing_t.py`

### 类

#### `class TrendSwingConfig`

偏波段的趋势突破策略参数。

说明：默认值仅作为兜底，建议在 `config/config.yaml` 的
`strategy.params` 下配置，便于回测与实盘保持一致。

#### `class TrendSwingTStrategy(Strategy)`

趋势突破 + ATR 风控 + 目标仓位管理 + 低频做T（可选）。

**方法:**

- `__init__(self, config) -> None`
- `analyze(self, symbol, df) -> Dict[Any]`
- `_reset_symbol(self, symbol) -> None`

### 函数

#### `def _calculate_rsi_fast(df, period, column) -> Any`

---

## 文件: `app\trading\account.py`

### 类

#### `class PaperAccount`

模拟交易账户，用于实时模拟盘。

**方法:**

- `__init__(self, initial_capital, commission_rate, on_trade) -> None`
- `set_stock_names(self, names) -> None`
  - 设置股票名称映射
- `record_equity(self, time, equity) -> None`
  - 记录当前权益。
- `get_trade_stats(self) -> Dict[Any]`
  - 计算交易统计信息，包括胜率等。
- `update_price(self, symbol, price) -> None`
  - 更新股票最新价格
- `get_total_equity(self) -> float`
  - 计算当前总权益（现金 + 持仓市值）
- `buy(self, symbol, price, quantity, time, reason, signal_id, factors, trade_tag) -> bool`
  - 执行模拟买入
- `sell(self, symbol, price, quantity, time, reason, signal_id, factors, trade_tag) -> bool`
  - 执行模拟卖出（quantity 可小于当前持仓，从而实现减仓/做T）

---

## 文件: `app\trading\executor.py`

### 类

#### `class TradeExecutor`

交易执行器，负责处理交易信号并操作账户。
封装了买入和卖出的具体逻辑，供回测和实盘共用。

约定：策略只输出 BUY / SELL / HOLD。
- BUY/SELL 由仓位管理器决定具体下单数量（可自然实现加仓/减仓/清仓）。

**方法:**

- `__init__(self, account, position_manager) -> None`
- `set_lot_sizes(self, lot_sizes) -> None`
  - 设置股票最小交易单位
- `execute(self, signal, symbol, time, price) -> Dict[Any]`
- `_normalize_quantity(self, symbol, quantity) -> int`
- `_buy(self, symbol, time, price, reason, signal_id, factors, result, requested_qty, trade_tag) -> None`
  - 执行买入逻辑
- `_sell(self, symbol, time, price, reason, signal_id, factors, result, requested_qty, trade_tag) -> None`
  - 执行卖出逻辑

---

## 文件: `app\trading\persistence.py`

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

## 文件: `app\trading\position.py`

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

## 文件: `app\utils\finance.py`

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

## 文件: `app\utils\formatting.py`

### 函数

#### `def get_display_width(s) -> int`

计算字符串的显示宽度（东亚宽度）。

#### `def pad_string(s, width, align) -> str`

用空格填充字符串以达到目标显示宽度。
align: '<' 左对齐 (默认), '>' 右对齐

---

## 文件: `app\utils\indicators.py`

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

## 文件: `app\utils\notifier.py`

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

## 文件: `app\utils\plotter.py`

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

## 文件: `app\utils\reporting.py`

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

