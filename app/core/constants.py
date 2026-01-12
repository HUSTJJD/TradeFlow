from enum import Enum


class TradeMode(str, Enum):
    """交易模式枚举"""

    LIVE = "LIVE"
    PAPER = "PAPER"
    BACKTEST = "BACKTEST"


class SignalType(str, Enum):
    """交易信号类型枚举"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Market(str, Enum):
    """市场板块枚举"""

    SSE_MAIN = "SSE_MAIN"  # 上交所主板
    SSE_STAR = "SSE_STAR"  # 上交所科创板
    SZSE_MAIN = "SZSE_MAIN"  # 深交所主板
    SZSE_GEM = "SZSE_GEM"  # 深交所创业板
    HKCONNECT = "HKCONNECT"  # 港股通


class TradeStatus(str, Enum):
    """交易状态枚举"""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class TradeStraegy(str, Enum):
    """交易策略枚举"""

    MACD = "MACD"
    RSI = "RSI"
    TREND_SWING_T = "TREND_SWING_T"
    COMPOSITE = "COMPOSITE"


class ProviderType(str, Enum):
    """券商api枚举"""

    LONGPORT = "LONGPORT"


class NotifierType(str, Enum):
    """通知方式枚举"""

    EMAIL = "EMAIL"
