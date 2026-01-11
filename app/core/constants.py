from enum import Enum


class SignalType(str, Enum):
    """交易信号类型枚举"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
