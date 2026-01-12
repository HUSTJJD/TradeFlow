from .config import global_config
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

setup_logging(global_config.get("log_level", "INFO"))

__all__ = [
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
