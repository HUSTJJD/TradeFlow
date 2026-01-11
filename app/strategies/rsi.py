from typing import Dict, Any
import pandas as pd
from .base import Strategy
from app.utils.indicators import calculate_rsi
from app.core.constants import SignalType


class RSIStrategy(Strategy):
    """
    相对强弱指数 (RSI) 策略。
    """

    def __init__(
        self, period: int = 14, overbought: int = 70, oversold: int = 30
    ) -> None:
        """
        初始化 RSI 策略。

        Args:
            period: RSI 计算周期。
            overbought: 超买阈值 (默认 70)。
            oversold: 超卖阈值 (默认 30)。
        """
        super().__init__()
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        使用 RSI 策略分析数据。

        RSI < 超卖 -> 买入
        RSI > 超买 -> 卖出
        """
        if len(df) < self.period + 1:
            return {"action": SignalType.HOLD, "reason": "数据不足"}

        df = calculate_rsi(df, self.period)

        last_row = df.iloc[-1]
        current_price = float(last_row["close"])
        current_rsi = float(last_row["rsi"])

        # 超卖
        if current_rsi < self.oversold:
            return {
                "action": SignalType.BUY,
                "price": current_price,
                "reason": f"RSI 超卖 ({current_rsi:.2f} < {self.oversold})",
                "factors": {
                    "rsi": current_rsi,
                    "threshold": self.oversold,
                },
            }

        # 超买
        elif current_rsi > self.overbought:
            return {
                "action": SignalType.SELL,
                "price": current_price,
                "reason": f"RSI 超买 ({current_rsi:.2f} > {self.overbought})",
                "factors": {
                    "rsi": current_rsi,
                    "threshold": self.overbought,
                },
            }

        return {"action": SignalType.HOLD, "reason": f"RSI 中性 ({current_rsi:.2f})"}
