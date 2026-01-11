from typing import List, Dict, Any, Optional
import logging
import pandas as pd
from .base import Strategy
from app.core.constants import SignalType

logger = logging.getLogger(__name__)


class CompositeStrategy(Strategy):
    """
    组合策略，结合多个子策略。
    """

    def __init__(self, strategies: List[Strategy], mode: str = "consensus", 
                 name: Optional[str] = None, description: str = "") -> None:
        """
        初始化组合策略。

        Args:
            strategies: 策略实例列表。
            mode: 决策模式。
                  'consensus': 所有策略必须一致。
                  'any': 任意策略触发信号（卖出优先）。
                  'vote': 多数投票。
            name: 策略名称，默认使用类名
            description: 策略描述
        """
        if name is None:
            name = f"Composite_{mode}"
        if not description:
            description = f"组合策略，模式：{mode}"
            
        super().__init__(name=name, description=description)
        self.strategies = strategies
        self.mode = mode
        self._valid_modes = ["consensus", "any", "vote"]

    def _on_initialize(self, **kwargs: Any) -> bool:
        """组合策略初始化"""
        # 验证模式有效性
        if self.mode not in self._valid_modes:
            raise ValueError(f"无效的模式: {self.mode}，有效模式: {self._valid_modes}")
        
        # 验证子策略
        if not self.strategies:
            raise ValueError("组合策略必须包含至少一个子策略")
        
        for i, strategy in enumerate(self.strategies):
            if not isinstance(strategy, Strategy):
                raise ValueError(f"第{i+1}个子策略不是Strategy实例")
        
        # 初始化所有子策略
        for strategy in self.strategies:
            if not strategy._initialized:
                strategy.initialize()
        
        logger.info(f"组合策略初始化完成，包含{len(self.strategies)}个子策略，模式：{self.mode}")
        return True

    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        使用多个策略分析数据并合并结果。
        """
        # 数据验证
        if not self.validate_data(df, ['close']):
            return {"action": SignalType.HOLD, "reason": "数据无效"}

        signals = []
        for strategy in self.strategies:
            try:
                sig = strategy.analyze(symbol, df)
                signals.append(sig)
            except Exception as e:
                logger.error(f"子策略 {strategy.name} 失败: {e}")
                signals.append({"action": SignalType.HOLD, "reason": "错误"})

        # 决策逻辑
        buy_count = sum(1 for s in signals if s["action"] == SignalType.BUY)
        sell_count = sum(1 for s in signals if s["action"] == SignalType.SELL)
        total = len(signals)

        current_price = float(df.iloc[-1]["close"]) if not df.empty else 0.0

        reasons = [
            f"{strategy.name}: {sig['action']}"
            for strategy, sig in zip(self.strategies, signals)
        ]
        combined_reason = " | ".join(reasons)

        # 收集因子
        combined_factors = {}
        for strategy, sig in zip(self.strategies, signals):
            if "factors" in sig:
                combined_factors[strategy.name] = sig["factors"]

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

    def add_strategy(self, strategy: Strategy) -> None:
        """
        添加子策略到组合中。
        
        Args:
            strategy: 要添加的策略实例
        """
        if not isinstance(strategy, Strategy):
            raise ValueError("只能添加Strategy实例")
        
        self.strategies.append(strategy)
        
        # 如果策略已初始化，初始化新添加的策略
        if self._initialized and not strategy._initialized:
            strategy.initialize()
        
        logger.info(f"已添加子策略: {strategy.name}")

    def remove_strategy(self, strategy_name: str) -> bool:
        """
        从组合中移除指定名称的子策略。
        
        Args:
            strategy_name: 要移除的策略名称
            
        Returns:
            bool: 是否成功移除
        """
        for i, strategy in enumerate(self.strategies):
            if strategy.name == strategy_name:
                removed = self.strategies.pop(i)
                removed.cleanup()
                logger.info(f"已移除子策略: {strategy_name}")
                return True
        
        logger.warning(f"未找到要移除的子策略: {strategy_name}")
        return False

    def get_info(self) -> Dict[str, Any]:
        """获取组合策略的详细信息"""
        base_info = super().get_info()
        base_info.update({
            "mode": self.mode,
            "sub_strategies": [strategy.get_info() for strategy in self.strategies],
            "sub_strategy_count": len(self.strategies)
        })
        return base_info

    def _on_cleanup(self) -> None:
        """清理所有子策略资源"""
        for strategy in self.strategies:
            strategy.cleanup()
        logger.info("所有子策略已清理")
