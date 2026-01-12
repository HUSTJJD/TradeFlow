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

    MAIN = "Main"  # 主板
    STAR = "STAR"  # 科创板
    CHINEXT = "ChiNext"  # 创业板
    BSHARE = "BShare"  # B股
    BSE = "BSE"  # 北交所
    NQ = "NQ"  # 新三板
    HK = "HK"  # 港股通


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
