from .config import load_app_config
from .logger import setup_logging

from .constants import (
    TradeMode,
    ActionType,
    MarketType,
    TradeStatus,
    StraegyName,
    ProviderName,
    NotifierType,
    SYMBOL_REGEX,
    HEXCOLOR_REGEX,
    TIME_FORMAT,
)

try:
    cfg = load_app_config()
except Exception as e:
    print(f"Failed to load app config: {e}")
    raise
setup_logging(cfg.app.log_level)

__all__ = [
    "cfg",
    "TradeMode",
    "ActionType",
    "MarketType",
    "TradeStatus",
    "StraegyName",
    "ProviderName",
    "NotifierType",
    "SYMBOL_REGEX",
    "HEXCOLOR_REGEX",
    "TIME_FORMAT",
]
