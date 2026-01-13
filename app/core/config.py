import os
import yaml
from typing import Any, List, Dict, Optional
from dataclasses import dataclass, field, fields, is_dataclass
from .singleton import singleton_threadsafe

@dataclass
class LongPortConfig:
    app_key: str = ""
    app_secret: str = ""
    access_token: str = ""


@dataclass
class EmailConfig:
    smtp_server: str = ""
    smtp_port: int = 465
    sender_email: str = ""
    sender_password: str = ""
    receiver_emails: List[str] = field(default_factory=list)


@dataclass
class BacktestConfig:
    start_time: str = "2023-01-01"
    end_time: str = "2023-12-31"
    benchmarks: List[str] = field(default_factory=list)
    initial_balance: float = 100000.0
    commission_rate: float = 0.0003
    position_ratio: float = 0.2
    warmup_days: Dict[str, Any] = field(
        default_factory=dict
    )  # Based on usage: get(..., {})
    multi_timeframe: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PositionSizingConfig:
    max_position_ratio: float = 0.25
    risk_per_trade: float = 0.01
    atr_stop_multiple: float = 2.5
    min_rebalance_ratio: float = 0.05


@dataclass
class MonitorConfig:
    interval: int = 60
    request_delay: float = 0.5


@dataclass
class TradingConfig:
    initial_balance: float = 1000000.0
    position_ratio: float = 0.2
    total_capital: float = 100000.0
    allowed_boards: List[str] = field(default_factory=list)
    position_sizing: PositionSizingConfig = field(default_factory=PositionSizingConfig)
    monitor: MonitorConfig = field(default_factory=MonitorConfig)
    commission_rate: float = 0.0003


@dataclass
class BenchmarkColorConfig:
    symbol: str = ""
    color: str = ""


@dataclass
class ReportConfig:
    account: str = "#1f77b4"
    buy: str = "#2ca02c"
    sell: str = "#d62728"
    benchmarks: List[BenchmarkColorConfig] = field(default_factory=list)


@dataclass
class UniverseSelectorConfig:
    max_symbols: int = 5
    one_per_industry: bool = True


@dataclass
class UniverseRefreshConfig:
    lookback_days: int = 120
    sentiment_window_days: int = 7


@dataclass
class UniverseConfig:
    selector: UniverseSelectorConfig = field(default_factory=UniverseSelectorConfig)
    refresh: UniverseRefreshConfig = field(default_factory=UniverseRefreshConfig)


@dataclass
class MarketDataConfig:
    update_interval_days: int = 7


@dataclass
class StrategyMultiTimeframeConfig:
    swing_timeframe: str = "1d"
    t_timeframe: str = "15m"


@dataclass
class StrategyConfig:
    name: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    multi_timeframe: StrategyMultiTimeframeConfig = field(
        default_factory=StrategyMultiTimeframeConfig
    )


def _convert_value(value: Any, target_type: Any) -> Any:
    if value is None:
        return None

    # dataclass
    if isinstance(target_type, type) and is_dataclass(target_type):
        if isinstance(value, dict):
            return _dataclass_from_dict(target_type, value)
        return value

    origin = getattr(target_type, "__origin__", None)
    args = getattr(target_type, "__args__", ())

    if origin in (list, List):
        elem_type = args[0] if args else Any
        if isinstance(value, list):
            return [_convert_value(v, elem_type) for v in value]
        return value

    if origin in (dict, Dict):
        key_type = args[0] if len(args) >= 1 else Any
        val_type = args[1] if len(args) >= 2 else Any
        if isinstance(value, dict):
            return {
                _convert_value(k, key_type): _convert_value(v, val_type)
                for k, v in value.items()
            }
        return value

    return value


def _dataclass_from_dict(cls: type, data: Dict[str, Any]):
    kwargs: Dict[str, Any] = {}
    for f in fields(cls):
        if f.name in data:
            kwargs[f.name] = _convert_value(data[f.name], f.type)
    return cls(**kwargs)


def _get_by_dotted_key(obj: Any, key: str, default: Any = None) -> Any:
    if not key:
        return obj

    value = obj
    for part in key.split("."):
        if value is None:
            return default

        if isinstance(value, dict):
            value = value.get(part)
            continue

        if hasattr(value, part):
            value = getattr(value, part)
            continue

        return default

    return default if value is None else value


@singleton_threadsafe
class AppConfig(yaml.YAMLObject):
    """应用程序配置对象。

    说明：
    - YAML 中的 `!AppConfig` 属于 PyYAML tag。
    - **运行时解析该 tag，必须使用** `yaml.load(..., Loader=yaml.FullLoader)`。
    - IDE / YAML 校验器提示 `Unresolved tag: !AppConfig` 是静态提示，不影响运行。
      若要消除提示，可在编辑器配置 `yaml.customTags`。
    """

    yaml_tag = "!AppConfig"

    # 这些属性必须作为“类属性”声明，IDE 才能识别；同时也更符合类型检查
    longport: LongPortConfig
    email: EmailConfig
    log_level: str
    run_mode: str
    notifier_type: str
    backtest: BacktestConfig
    trading: TradingConfig
    report: ReportConfig
    universe: UniverseConfig
    market_data: MarketDataConfig
    strategy: StrategyConfig
    markets: List[str]
    plot: Dict[str, Any]
    data: Dict[str, Any]

    def __init__(
        self,
        longport: Optional[LongPortConfig] = None,
        email: Optional[EmailConfig] = None,
        log_level: str = "INFO",
        run_mode: str = "backtest",
        notifier_type: str = "",
        backtest: Optional[BacktestConfig] = None,
        trading: Optional[TradingConfig] = None,
        report: Optional[ReportConfig] = None,
        universe: Optional[UniverseConfig] = None,
        market_data: Optional[MarketDataConfig] = None,
        strategy: Optional[StrategyConfig] = None,
        markets: Optional[List[str]] = None,
        plot: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.longport = longport or LongPortConfig()
        self.email = email or EmailConfig()
        self.log_level = log_level
        self.run_mode = run_mode
        self.notifier_type = notifier_type
        self.backtest = backtest or BacktestConfig()
        self.trading = trading or TradingConfig()
        self.report = report or ReportConfig()
        self.universe = universe or UniverseConfig()
        self.market_data = market_data or MarketDataConfig()
        self.strategy = strategy or StrategyConfig()
        self.markets = markets or []
        self.plot = plot or {}
        self.data = data or {}

    def __repr__(self) -> str:
        return "AppConfig()"

    @classmethod
    def __from_yaml__(cls, loader, node):
        raw = loader.construct_mapping(node, deep=True)
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "AppConfig":
        return cls(
            longport=_convert_value(raw.get("longport"), LongPortConfig),
            email=_convert_value(raw.get("email"), EmailConfig),
            log_level=raw.get("log_level", "INFO"),
            run_mode=raw.get("run_mode", "backtest"),
            notifier_type=raw.get("notifier_type", ""),
            backtest=_convert_value(raw.get("backtest"), BacktestConfig),
            trading=_convert_value(raw.get("trading"), TradingConfig),
            report=_convert_value(raw.get("report"), ReportConfig),
            universe=_convert_value(raw.get("universe"), UniverseConfig),
            market_data=_convert_value(raw.get("market_data"), MarketDataConfig),
            strategy=_convert_value(raw.get("strategy"), StrategyConfig),
            markets=_convert_value(raw.get("markets"), List[str]) or [],
            plot=_convert_value(raw.get("plot"), Dict[str, Any]) or {},
            data=_convert_value(raw.get("data"), Dict[str, Any]) or {},
        )

    def get(self, key: str = "", default: Any = None) -> Any:
        """兼容旧代码：支持 `global_config.get('a.b.c')`。"""
        return _get_by_dotted_key(self, key, default)


def load_app_config() -> AppConfig:
    current = os.path.dirname(__file__)
    while os.path.basename(current) != "app":
        current = os.path.dirname(current)
    base_dir = os.path.dirname(current)
    config_path = os.path.join(base_dir, "config", "config.yaml")

    if not os.path.exists(config_path):
        return AppConfig()

    with open(config_path, "r", encoding="utf-8") as f:
        # 必须用 yaml.load 才会触发 `!AppConfig` 解析
        loaded = yaml.load(f, Loader=yaml.FullLoader)

    if isinstance(loaded, AppConfig):
        return loaded

    # 兼容：如果用户移除了 !AppConfig（比如为消除 IDE 报错），仍可工作
    if isinstance(loaded, dict):
        return AppConfig.from_dict(loaded)

    return AppConfig()
