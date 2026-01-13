from .config import AppConfig, load_app_config
from .logger import setup_logging
from .singleton import singleton_threadsafe
from .constants import (
    TradeMode,
    SignalType,
    Market,
    TradeStatus,
    TradeStraegy,
    ProviderType,
    NotifierType,
)
global_config = load_app_config()
setup_logging(global_config.log_level)

__all__ = [
    "AppConfig",
    "global_config",
    "singleton_threadsafe",
    "TradeMode",
    "SignalType",
    "Market",
    "TradeStatus",
    "TradeStraegy",
    "ProviderType",
    "NotifierType",
]
