import os
from typing import List

import yaml
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .constants import Market, NotifierType, ProviderType, TradeMode, TradeStraegy


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


class AppConfig(BaseModel):
    log_level: str = "INFO"
    run_mode: TradeMode = TradeMode.BACKTEST
    notifier_type: NotifierType = NotifierType.EMAIL
    using_provider: ProviderType = ProviderType.LONGPORT
    using_strategy: TradeStraegy = TradeStraegy.MACD
    allowed_boards: List[Market] = Field(default_factory=list)
    update_market_data_interval_days: int = 7


class BacktestConfig(BaseModel):
    start_time: str = "2023-01-01"
    end_time: str = "2023-12-31"
    benchmarks: List[str] = Field(default_factory=list)


class AccountConfig(BaseModel):
    balance: float = 1000000.0
    history_count: int = 100
    max_trades_per_symbol_per_day: int = 2
    position_ratio: float = 0.2


class PositionSizingConfig(BaseModel):
    max_position_ratio: float = 0.25
    risk_per_trade: float = 0.01
    atr_stop_multiple: float = 2.5
    min_rebalance_ratio: float = 0.05


class MonitorConfig(BaseModel):
    interval: int = 60
    request_delay: float = 0.5


class TradingConfig(BaseModel):
    enable_t: bool = True
    initial_balance: float = 1000000.0
    total_capital: float = 100000.0
    monitor: MonitorConfig = Field(default_factory=MonitorConfig)
    position_sizing: PositionSizingConfig = Field(default_factory=PositionSizingConfig)


class BenchmarkColorConfig(BaseModel):
    symbol: str = ""
    color: str = ""


class ReportConfig(BaseModel):
    account: str = "#1f77b4"
    buy: str = "#2ca02c"
    sell: str = "#d62728"
    benchmarks: List[BenchmarkColorConfig] = Field(default_factory=list)


class WRConfig(BaseModel):
    period: int = 14
    threshold: float = 0.02


class MACDConfig(BaseModel):
    fast: int = 12
    slow: int = 26
    signal: int = 9


class RSIConfig(BaseModel):
    period: int = 14
    overbought: int = 70
    oversold: int = 30


class TradeFlowConfig(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        frozen=True,
        extra="forbid",
    )

    # region 隐私配置
    longport: LongPortConfig = Field(default_factory=LongPortConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    # endregion

    # region 全局配置
    app: AppConfig = Field(default_factory=AppConfig)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    account: AccountConfig = Field(default_factory=AccountConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    # endregion

    # region 策略配置
    WR: WRConfig = Field(default_factory=WRConfig)
    MACD: MACDConfig = Field(default_factory=MACDConfig)
    RSI: RSIConfig = Field(default_factory=RSIConfig)
    # endregion


def load_app_config() -> TradeFlowConfig:
    current = os.path.dirname(__file__)
    while os.path.basename(current) != "app":
        current = os.path.dirname(current)
    base_dir = os.path.dirname(current)
    config_path = os.path.join(base_dir, "config", "config.yaml")

    with open(config_path, "r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}

    if not isinstance(loaded, dict):
        loaded = {}

    return TradeFlowConfig(**loaded)
