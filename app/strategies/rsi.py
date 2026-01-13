from typing import Dict, Any
import pandas as pd
from .strategy import Strategy
from app.utils.indicators import calculate_rsi
from app.core.constants import ActionType


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
            overbought: 超买阈值。
            oversold: 超卖阈值。
        """
        super().__init__(
            name="RSI", description="相对强弱指数策略，基于RSI超买超卖信号"
        )
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
        self._min_data_length = period + 1

    def _on_initialize(self, **kwargs: Any) -> bool:
        """RSI策略初始化"""
        # 验证参数有效性
        if self.period <= 0:
            raise ValueError("RSI周期必须为正整数")
        if self.overbought <= self.oversold:
            raise ValueError("超买阈值必须大于超卖阈值")
        if self.overbought <= 50 or self.oversold >= 50:
            raise ValueError("超买阈值应大于50，超卖阈值应小于50")

        return True

    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        使用 RSI 策略分析数据。

        超卖: RSI < 超卖阈值 -> 买入
        超买: RSI > 超买阈值 -> 卖出
        """
        # 数据验证
        if not self.validate_data(df, ["close"]):
            return {"action": ActionType.HOLD, "reason": "数据无效"}

        if len(df) < self._min_data_length:
            return {"action": ActionType.HOLD, "reason": "数据不足"}

        # 计算RSI指标
        df = calculate_rsi(df, self.period)

        # 获取最后一个数据点
        last_row = df.iloc[-1]
        current_price = float(last_row["close"])
        rsi_value = float(last_row["rsi"])

        # 超卖信号
        if rsi_value < self.oversold:
            return {
                "action": ActionType.BUY,
                "price": current_price,
                "reason": f"RSI 超卖 ({rsi_value:.1f} < {self.oversold})",
                "factors": {
                    "rsi": rsi_value,
                    "oversold_threshold": self.oversold,
                    "overbought_threshold": self.overbought,
                },
            }

        # 超买信号
        if rsi_value > self.overbought:
            return {
                "action": ActionType.SELL,
                "price": current_price,
                "reason": f"RSI 超买 ({rsi_value:.1f} > {self.overbought})",
                "factors": {
                    "rsi": rsi_value,
                    "oversold_threshold": self.oversold,
                    "overbought_threshold": self.overbought,
                },
            }

        return {"action": ActionType.HOLD, "reason": "无信号"}

    def get_info(self) -> Dict[str, Any]:
        """获取RSI策略的详细信息"""
        base_info = super().get_info()
        base_info.update(
            {
                "parameters": {
                    "period": self.period,
                    "overbought": self.overbought,
                    "oversold": self.oversold,
                    "min_data_length": self._min_data_length,
                }
            }
        )
        return base_info
