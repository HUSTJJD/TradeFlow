from .config import load_app_config
from .logger import setup_logging
from .singleton import singleton_threadsafe
from .constants import (
    TradeMode,
    SignalType,
    MarketType,
    TradeStatus,
    StraegyName,
    ProviderName,
    NotifierType,
)
try:
    cfg = load_app_config()
except Exception as e:
    print(f"Failed to load app config: {e}")
    raise
setup_logging(cfg.app.log_level)

__all__ = [
    "cfg",
    "singleton_threadsafe",
    "TradeMode",
    "SignalType",
    "MarketType",
    "TradeStatus",
    "StraegyName",
    "ProviderName",
    "NotifierType",
]
