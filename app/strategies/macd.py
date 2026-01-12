from typing import Dict, Any
import pandas as pd
from .base import Strategy
from app.utils.indicators import calculate_macd
from app.core.constants import SignalType


class MACDStrategy(Strategy):
    """
    移动平均收敛散度 (MACD) 策略。
    """

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9) -> None:
        """
        初始化 MACD 策略。

        Args:
            fast: 快速 EMA 周期。
            slow: 慢速 EMA 周期。
            signal: 信号线 EMA 周期。
        """
        super().__init__(
            name="MACD", description="移动平均收敛散度策略，基于MACD金叉死叉信号"
        )
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self._min_data_length = slow + signal

    def _on_initialize(self, **kwargs: Any) -> bool:
        """MACD策略初始化"""
        # 验证参数有效性
        if self.fast <= 0 or self.slow <= 0 or self.signal <= 0:
            raise ValueError("MACD参数必须为正整数")
        if self.fast >= self.slow:
            raise ValueError("快速EMA周期必须小于慢速EMA周期")

        return True

    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        使用 MACD 策略分析数据。

        金叉: DIF 上穿 DEA -> 买入
        死叉: DIF 下穿 DEA -> 卖出
        """
        # 数据验证
        if not self.validate_data(df, ["close"]):
            return {"action": SignalType.HOLD, "reason": "数据无效"}

        if len(df) < self._min_data_length:
            return {"action": SignalType.HOLD, "reason": "数据不足"}

        # 计算MACD指标
        df = calculate_macd(df, self.fast, self.slow, self.signal)

        # 获取最后两个数据点
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        current_price = float(last_row["close"])

        # 金叉
        if prev_row["dif"] < prev_row["dea"] and last_row["dif"] > last_row["dea"]:
            return {
                "action": SignalType.BUY,
                "price": current_price,
                "reason": f"MACD 金叉 (DIF: {last_row['dif']:.3f}, DEA: {last_row['dea']:.3f})",
                "factors": {
                    "dif": float(last_row["dif"]),
                    "dea": float(last_row["dea"]),
                    "macd": float(last_row["macd"]),
                },
            }

        # 死叉
        elif prev_row["dif"] > prev_row["dea"] and last_row["dif"] < last_row["dea"]:
            return {
                "action": SignalType.SELL,
                "price": current_price,
                "reason": f"MACD 死叉 (DIF: {last_row['dif']:.3f}, DEA: {last_row['dea']:.3f})",
                "factors": {
                    "dif": float(last_row["dif"]),
                    "dea": float(last_row["dea"]),
                    "macd": float(last_row["macd"]),
                },
            }

        return {"action": SignalType.HOLD, "reason": "无信号"}

    def get_info(self) -> Dict[str, Any]:
        """获取MACD策略的详细信息"""
        base_info = super().get_info()
        base_info.update(
            {
                "parameters": {
                    "fast": self.fast,
                    "slow": self.slow,
                    "signal": self.signal,
                    "min_data_length": self._min_data_length,
                }
            }
        )
        return base_info
