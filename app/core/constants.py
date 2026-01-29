from enum import Enum

SYMBOL_REGEX = r"^[a-zA-Z0-9\.]*\.[a-zA-Z0-9]+$"

HEXCOLOR_REGEX = r"^#[0-9a-fA-F]{6}$"

class TradeMode(str, Enum):
    """交易模式枚举"""

    LIVE = "LIVE"
    PAPER = "PAPER"
    BACKTEST = "BACKTEST"


class ActionType(str, Enum):
    """交易信号类型枚举"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class MarketType(str, Enum):
    """市场板块枚举"""

    # 美股市场
    US_MAIN = "USMain"  # 美股主板
    US_PINK = "USPink"  # 粉单市场
    US_DJI = "USDJI"  # 道琼斯指数
    US_NSDQ = "USNSDQ"  # 纳斯达克指数
    US_SECTOR = "USSector"  # 美股行业概念
    US_OPTION = "USOption"  # 美股期权
    US_OPTION_S = "USOptionS"  # 美股特殊期权（收盘时间为 16:15）

    # 港股市场
    HK_EQUITY = "HKEquity"  # 港股股本证券
    HK_PRE_IPO = "HKPreIPO"  # 港股暗盘
    HK_WARRANT = "HKWarrant"  # 港股轮证
    HK_HS = "HKHS"  # 恒生指数
    HK_SECTOR = "HKSector"  # 港股行业概念

    # A股市场
    SH_MAIN_CONNECT = "SHMainConnect"  # 上证主板 - 互联互通
    SH_MAIN_NON_CONNECT = "SHMainNonConnect"  # 上证主板 - 非互联互通
    SH_STAR = "SHSTAR"  # 科创板
    CN_IX = "CNIX"  # 沪深指数
    CN_SECTOR = "CNSector"  # 沪深行业概念
    SZ_MAIN_CONNECT = "SZMainConnect"  # 深证主板 - 互联互通
    SZ_MAIN_NON_CONNECT = "SZMainNonConnect"  # 深证主板 - 非互联互通
    SZ_GEM_CONNECT = "SZGEMConnect"  # 创业板 - 互联互通
    SZ_GEM_NON_CONNECT = "SZGEMNonConnect"  # 创业板 - 非互联互通

    # 新加坡市场
    SG_MAIN = "SGMain"  # 新加坡主板
    STI = "STI"  # 新加坡海峡指数
    SG_SECTOR = "SGSector"  # 新加坡行业概念


class TradeStatus(str, Enum):
    """交易状态枚举"""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class StraegyName(str, Enum):
    """交易策略枚举"""

    MACD = "MACD"
    RSI = "RSI"


class ProviderName(str, Enum):
    """券商api枚举"""

    LONGPORT = "LONGPORT"


class NotifierType(str, Enum):
    """通知方式枚举"""

    EMAIL = "EMAIL"
