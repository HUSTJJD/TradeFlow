import os
from typing import Any, Dict, List
import yaml
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LongPortConfig(BaseModel):
    app_key: str = ""
    app_secret: str = ""
    access_token: str = ""


class EmailConfig(BaseModel):
    smtp_server: str = ""
    smtp_port: int = 465
    sender_email: EmailStr = ""
    sender_password: str = ""
    receiver_emails: List[EmailStr] = Field(default_factory=list)


class BacktestConfig(BaseModel):
    start_time: str = "2023-01-01"
    end_time: str = "2023-12-31"
    benchmarks: List[str] = Field(default_factory=list)


class PositionSizingConfig(BaseModel):
    max_position_ratio: float = 0.25
    risk_per_trade: float = 0.01
    atr_stop_multiple: float = 2.5
    min_rebalance_ratio: float = 0.05


class MonitorConfig(BaseModel):
    interval: int = 60
    request_delay: float = 0.5


class TradingConfig(BaseModel):
    initial_balance: float = 1000000.0
    position_ratio: float = 0.2
    total_capital: float = 100000.0
    allowed_boards: List[str] = Field(default_factory=list)
    position_sizing: PositionSizingConfig = Field(default_factory=PositionSizingConfig)
    monitor: MonitorConfig = Field(default_factory=MonitorConfig)


class BenchmarkColorConfig(BaseModel):
    symbol: str = ""
    color: str = ""


class ReportConfig(BaseModel):
    account: str = "#1f77b4"
    buy: str = "#2ca02c"
    sell: str = "#d62728"
    benchmarks: List[BenchmarkColorConfig] = Field(default_factory=list)


class UniverseSelectorConfig(BaseModel):
    max_symbols: int = 5
    one_per_industry: bool = True


class UniverseRefreshConfig(BaseModel):
    lookback_days: int = 120
    sentiment_window_days: int = 7


class UniverseConfig(BaseModel):
    selector: UniverseSelectorConfig = Field(default_factory=UniverseSelectorConfig)
    refresh: UniverseRefreshConfig = Field(default_factory=UniverseRefreshConfig)


class MarketDataConfig(BaseModel):
    update_interval_days: int = 7


class StrategyMultiTimeframeConfig(BaseModel):
    swing_timeframe: str = "1d"
    t_timeframe: str = "15m"


class StrategyConfig(BaseModel):
    name: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)
    multi_timeframe: StrategyMultiTimeframeConfig = Field(
        default_factory=StrategyMultiTimeframeConfig
    )


class AppConfig(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,  # 自动去除字符串首尾空格
        validate_assignment=True,  # 赋值时也验证
        frozen=True,  # 不可变对象
        extra="forbid",  # 禁止额外字段
    )

    longport: LongPortConfig = Field(default_factory=LongPortConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)

    log_level: str = "INFO"
    run_mode: str = "backtest"
    notifier_type: str = "email"

    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    universe: UniverseConfig = Field(default_factory=UniverseConfig)
    market_data: MarketDataConfig = Field(default_factory=MarketDataConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)

    markets: List[str] = Field(default_factory=list)
    plot: Dict[str, Any] = Field(default_factory=dict)
    data: Dict[str, Any] = Field(default_factory=dict)


def load_app_config() -> AppConfig:
    current = os.path.dirname(__file__)
    while os.path.basename(current) != "app":
        current = os.path.dirname(current)
    base_dir = os.path.dirname(current)
    config_path = os.path.join(base_dir, "config", "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}
    if not isinstance(loaded, dict):
        loaded = {}
    return AppConfig(**loaded)
