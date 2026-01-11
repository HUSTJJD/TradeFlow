from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.core.config import global_config
from app.core.constants import SignalType


@dataclass(frozen=True)
class PositionSizingConfig:
    """仓位管理参数（风险预算 + 再平衡 + 低频交易）。"""

    max_position_ratio: float = 0.25
    risk_per_trade: float = 0.01
    atr_stop_multiple: float = 2.5
    min_rebalance_ratio: float = 0.05


class PositionManager:
    """管理仓位规模、资金分配与再平衡。"""

    def __init__(
        self,
        position_ratio: float = 0.2,
        config: Optional[PositionSizingConfig] = None,
    ) -> None:
        # YAML 覆盖：trading.position_ratio 与 trading.position_sizing
        self.position_ratio = float(global_config.get("trading.position_ratio", position_ratio))

        if config is None:
            cfg_dict = global_config.get("trading.position_sizing", {}) or {}
            merged = {
                "max_position_ratio": cfg_dict.get("max_position_ratio", self.position_ratio),
                "risk_per_trade": cfg_dict.get("risk_per_trade", 0.01),
                "atr_stop_multiple": cfg_dict.get("atr_stop_multiple", 2.5),
                "min_rebalance_ratio": cfg_dict.get("min_rebalance_ratio", 0.05),
            }
            config = PositionSizingConfig(**merged)

        self.cfg = config

    def _normalize_quantity(self, quantity: int, lot_size: int = 1) -> int:
        if quantity <= 0:
            return 0
        if lot_size <= 1:
            return int(quantity)
        return int(quantity // lot_size) * lot_size

    def calculate_target_position_ratio(self, signal: Dict[str, Any]) -> float:
        """根据策略因子计算目标仓位比例。

        约定：策略可在 `signal['factors']` 里提供：
        - `atr`: ATR
        - `close`: 现价

        返回：0~max_position_ratio
        """
        factors = signal.get("factors") or {}
        price = float(factors.get("close") or 0.0)
        atr = float(factors.get("atr") or 0.0)

        # 缺少波动信息时，退化为固定仓位
        if price <= 0 or atr <= 0:
            return min(self.position_ratio, self.cfg.max_position_ratio)

        # 用 ATR 估算止损距离，结合风险预算得到“允许买入股数”
        # risk_amount = equity * risk_per_trade
        # stop_distance = atr * atr_stop_multiple
        # shares = risk_amount / stop_distance
        # 但这里不直接用 equity（在下单函数里计算），这里只返回一个“建议强度”
        vol_ratio = atr / price
        if vol_ratio <= 0:
            return min(self.position_ratio, self.cfg.max_position_ratio)

        # 简化的波动缩放：波动越大，目标仓位越小
        # 让 vol_ratio=2% 时接近 max_position_ratio，>5% 明显降低
        scaled = self.cfg.max_position_ratio * (0.02 / max(vol_ratio, 0.005))
        return max(0.0, min(self.cfg.max_position_ratio, scaled))

    def calculate_order_quantity(
        self,
        action: SignalType,
        current_position: int,
        price: float,
        total_equity: float,
        available_cash: float,
        lot_size: int = 1,
        signal: Optional[Dict[str, Any]] = None,
    ) -> int:
        """把 BUY/SELL 信号转换为具体下单数量（支持加/减仓）。

        规则：
        - `BUY`：把仓位调整到目标仓位（可能是加仓/建仓）
        - `SELL`：把仓位调整到更低目标（默认 0，即清仓）

        信号可选字段：
        - `target_position_ratio`: 目标仓位（0~max）
        - `target_shares`: 直接指定目标持仓股数（优先级最高）
        - `trade_tag`: "T" 时会启用更严格的最小交易阈值（避免频繁小单）
        """
        signal = signal or {}

        if price <= 0 or total_equity <= 0:
            return 0

        target_shares = signal.get("target_shares")
        if isinstance(target_shares, (int, float)):
            target_pos = max(0, int(target_shares))
        else:
            target_ratio = signal.get("target_position_ratio")
            if not isinstance(target_ratio, (int, float)):
                target_ratio = self.calculate_target_position_ratio(signal)

            target_amount = float(total_equity) * float(target_ratio)
            target_pos = int(target_amount / price)

        target_pos = self._normalize_quantity(target_pos, lot_size)

        if action == SignalType.BUY:
            delta = target_pos - current_position
            if delta <= 0:
                return 0

            # 现金约束
            max_affordable = int(available_cash / price)
            max_affordable = self._normalize_quantity(max_affordable, lot_size)
            delta = min(delta, max_affordable)

        elif action == SignalType.SELL:
            # 默认 SELL 视为降低仓位。若策略未指定目标仓位，则清仓。
            if "target_shares" in signal or "target_position_ratio" in signal:
                delta = current_position - target_pos
            else:
                delta = current_position

            if delta <= 0:
                return 0

            delta = min(delta, current_position)
            delta = self._normalize_quantity(delta, lot_size)

        else:
            return 0

        # 低频阈值：变化不足则不交易
        min_change = int(max(1, current_position) * self.cfg.min_rebalance_ratio)
        min_change = self._normalize_quantity(min_change, lot_size)
        if signal.get("trade_tag") == "T":
            # 做T更严格一些
            min_change = max(min_change, self._normalize_quantity(int(max(1, current_position) * 0.10), lot_size))

        if delta < min_change:
            return 0

        return int(delta)

    def get_position_suggestion(self, signal: Dict[str, Any], current_price: float, total_capital: float) -> str:
        action = signal.get("action")
        if action == SignalType.BUY:
            ratio = signal.get("target_position_ratio")
            if ratio is None:
                ratio = self.calculate_target_position_ratio(signal)
            return f"建议目标仓位: {float(ratio):.0%}（由仓位管理器按风险预算计算下单数量）"
        if action == SignalType.SELL:
            if "target_position_ratio" in signal or "target_shares" in signal:
                ratio = signal.get("target_position_ratio", "(指定)")
                return f"建议减仓/再平衡至目标仓位: {ratio}"
            return "建议动作: 清仓（SELL）"
        return ""
