from datetime import datetime
import os
from typing import List, Literal
from soupsieve import select_one
import yaml
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .constants import MarketType, NotifierType, ProviderName, TradeMode, StraegyName


class LongPortConfig(BaseModel):
    app_key: str = Field(default="", description="应用密钥")
    app_secret: str = Field(default="", description="应用密钥")
    access_token: str = Field(default="", description="访问令牌")


class EmailConfig(BaseModel):
    smtp_server: str = Field(default="", description="SMTP 服务器地址")
    smtp_port: int = Field(default=465, description="SMTP 端口号")
    sender_email: EmailStr = Field(default="", description="发件人邮箱")
    sender_password: str = Field(default="", description="发件人邮箱密码")
    receiver_emails: List[EmailStr] = Field(
        default_factory=list, description="收件人邮箱列表"
    )


class AppConfig(BaseModel):
    log_level: Literal["INFO", "DEBUG"] = Field(default="INFO", description="日志级别")
    notifier_type: NotifierType = Field(default=NotifierType.EMAIL)
    using_provider: ProviderName = Field(default=ProviderName.LONGPORT)
    using_strategy: StraegyName = Field(default=StraegyName.MACD)
    allowed_boards: List[MarketType] = Field(default_factory=list)
    update_market_data_interval_days: int = Field(default=1)


class BacktestConfig(BaseModel):
    start_time: datetime = Field(default_factory=datetime, description="开始时间")
    end_time: datetime = Field(default_factory=datetime, description="结束时间")
    benchmarks: List[str] = Field(default_factory=list, description="基准列表")


class AccountConfig(BaseModel):
    balance: float = Field(default=1000000.0, description="初始资金")
    history_count: int = Field(default=100, description="历史记录数量")
    max_trades_per_symbol_per_day: int = Field(
        default=2, description="每日每股票最大交易次数"
    )
    position_ratio: float = Field(default=0.2, description="仓位比例")


class PositionSizingConfig(BaseModel):
    max_position_ratio: float = Field(default=0.2, description="最大仓位比例")
    risk_per_trade: float = Field(default=0.01, description="每笔交易风险")
    atr_stop_multiple: float = Field(default=2.5, description="ATR止损倍数")
    min_rebalance_ratio: float = Field(default=0.05, description="最小再平衡比例")


class MonitorConfig(BaseModel):
    interval: int = Field(default=60, description="监控间隔")
    request_delay: float = Field(default=0.5, description="请求延迟")


class TradingConfig(BaseModel):
    enable_t: bool = Field(default=True, description="是否启用T日交易")
    initial_balance: float = Field(default=1000000.0, description="初始资金")
    total_capital: float = Field(default=100000.0, description="总资金")
    monitor: MonitorConfig = Field(
        default_factory=MonitorConfig, description="监控配置"
    )
    position_sizing: PositionSizingConfig = Field(
        default_factory=PositionSizingConfig, description="仓位配置"
    )


class BenchmarkColorConfig(BaseModel):
    symbol: str = Field(default="", description="股票代码")
    color: str = Field(
        default="#1f77b4", pattern=r"^#[0-9a-fA-F]{6}$", description="基准颜色配置"
    )


class ReportConfig(BaseModel):
    account: str = Field(
        default="#1f77b4", pattern=r"^#[0-9a-fA-F]{6}$", description="账户颜色配置"
    )
    buy: str = Field(
        default="#2ca02c", pattern=r"^#[0-9a-fA-F]{6}$", description="买入颜色配置"
    )
    sell: str = Field(
        default="#d62728", pattern=r"^#[0-9a-fA-F]{6}$", description="卖出颜色配置"
    )
    benchmarks: List[BenchmarkColorConfig] = Field(
        default_factory=list, description="基准颜色配置"
    )


class WRConfig(BaseModel):
    period: int = Field(default=14)
    threshold: float = Field(default=0.02)


class MACDConfig(BaseModel):
    fast: int = Field(default=12)
    slow: int = Field(default=26)
    signal: int = Field(default=9)


class RSIConfig(BaseModel):
    period: int = Field(default=14)
    overbought: int = Field(default=70)
    oversold: int = Field(default=30)


class TradeFlowConfig(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        frozen=True,
        extra="forbid",
    )

    # region 隐私配置
    longport: LongPortConfig = Field(
        default_factory=LongPortConfig, description="长桥配置"
    )
    email: EmailConfig = Field(default_factory=EmailConfig, description="邮箱配置")
    # endregion

    # region 全局配置
    app: AppConfig = Field(default_factory=AppConfig, description="应用配置")
    backtest: BacktestConfig = Field(
        default_factory=BacktestConfig, description="回测配置"
    )
    account: AccountConfig = Field(
        default_factory=AccountConfig, description="账户配置"
    )
    trading: TradingConfig = Field(
        default_factory=TradingConfig, description="交易配置"
    )
    report: ReportConfig = Field(default_factory=ReportConfig, description="报告配置")
    # endregion

    # region 策略配置
    WR: WRConfig = Field(default_factory=WRConfig, description="WR策略配置")
    MACD: MACDConfig = Field(default_factory=MACDConfig, description="MACD策略配置")
    RSI: RSIConfig = Field(default_factory=RSIConfig, description="RSI策略配置")
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
