from typing import List, Dict, Any
import logging
import pandas as pd
from .base import Strategy
from app.core.constants import SignalType

logger = logging.getLogger(__name__)


class CompositeStrategy(Strategy):
    """
    组合策略，结合多个子策略。
    """

    def __init__(self, strategies: List[Strategy], mode: str = "consensus") -> None:
        """
        初始化组合策略。

        Args:
            strategies: 策略实例列表。
            mode: 决策模式。
                  'consensus': 所有策略必须一致。
                  'any': 任意策略触发信号（卖出优先）。
                  'vote': 多数投票。
        """
        super().__init__()
        self.strategies = strategies
        self.mode = mode

    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        使用多个策略分析数据并合并结果。
        """
        signals = []
        for strategy in self.strategies:
            try:
                sig = strategy.analyze(symbol, df)
                signals.append(sig)
            except Exception as e:
                logger.error(f"子策略 {type(strategy).__name__} 失败: {e}")
                signals.append({"action": SignalType.HOLD, "reason": "错误"})

        # 决策逻辑
        buy_count = sum(1 for s in signals if s["action"] == SignalType.BUY)
        sell_count = sum(1 for s in signals if s["action"] == SignalType.SELL)
        total = len(signals)

        current_price = float(df.iloc[-1]["close"]) if not df.empty else 0.0

        reasons = [
            f"{type(s).__name__}: {sig['action']}"
            for s, sig in zip(self.strategies, signals)
        ]
        combined_reason = " | ".join(reasons)

        # 收集因子
        combined_factors = {}
        for strategy, sig in zip(self.strategies, signals):
            if "factors" in sig:
                combined_factors[type(strategy).__name__] = sig["factors"]

        if self.mode == "consensus":
            # 所有策略必须一致
            if buy_count == total:
                return {
                    "action": SignalType.BUY,
                    "price": current_price,
                    "reason": f"一致买入: {combined_reason}",
                    "factors": combined_factors,
                }
            elif sell_count == total:
                return {
                    "action": SignalType.SELL,
                    "price": current_price,
                    "reason": f"一致卖出: {combined_reason}",
                    "factors": combined_factors,
                }

        elif self.mode == "any":
            # 任意策略触发信号（风险管理优先卖出）
            if sell_count > 0:
                return {
                    "action": SignalType.SELL,
                    "price": current_price,
                    "reason": f"任意卖出: {combined_reason}",
                    "factors": combined_factors,
                }
            elif buy_count > 0:
                return {
                    "action": SignalType.BUY,
                    "price": current_price,
                    "reason": f"任意买入: {combined_reason}",
                    "factors": combined_factors,
                }

        elif self.mode == "vote":
            # 多数投票
            if buy_count > total / 2:
                return {
                    "action": SignalType.BUY,
                    "price": current_price,
                    "reason": f"多数买入: {combined_reason}",
                    "factors": combined_factors,
                }
            elif sell_count > total / 2:
                return {
                    "action": SignalType.SELL,
                    "price": current_price,
                    "reason": f"多数卖出: {combined_reason}",
                    "factors": combined_factors,
                }

        return {
            "action": SignalType.HOLD,
            "reason": f"无明确信号 ({self.mode}): {combined_reason}",
            "factors": combined_factors,
        }
