import logging
from typing import Dict, Any

from app.core.constants import SignalType
from app.trading.account import PaperAccount
from app.trading.position import PositionManager

logger = logging.getLogger(__name__)


class TradeExecutor:
    """
    交易执行器，负责处理交易信号并操作账户。
    封装了买入和卖出的具体逻辑，供回测和实盘共用。

    约定：策略只输出 BUY / SELL / HOLD。
    - BUY/SELL 由仓位管理器决定具体下单数量（可自然实现加仓/减仓/清仓）。
    """

    def __init__(self, account: PaperAccount, position_manager: PositionManager):
        self.account = account
        self.position_manager = position_manager
        self.lot_sizes: Dict[str, int] = {}

    def set_lot_sizes(self, lot_sizes: Dict[str, int]):
        """设置股票最小交易单位"""
        self.lot_sizes = lot_sizes

    def execute(self, signal: Dict[str, Any], symbol: str, time: Any, price: float) -> Dict[str, Any]:
        action = signal.get("action")
        reason = signal.get("reason", "")
        factors = signal.get("factors")
        trade_tag = signal.get("trade_tag")

        # 生成信号ID: symbol_time_action
        signal_id = f"{symbol}_{str(time)}_{action}"

        result = {
            "action": action,
            "symbol": symbol,
            "price": price,
            "time": time,
            "status": "SKIPPED",
            "quantity": 0,
            "msg": "",
        }

        if action not in (SignalType.BUY, SignalType.SELL):
            return result

        lot_size = int(self.lot_sizes.get(symbol, 1))
        current_equity = self.account.get_total_equity()
        current_pos = int(self.account.positions.get(symbol, 0))

        qty = self.position_manager.calculate_order_quantity(
            action=action,
            current_position=current_pos,
            price=price,
            total_equity=current_equity,
            available_cash=float(self.account.cash),
            lot_size=lot_size,
            signal={**signal, "trade_tag": trade_tag},
        )

        if qty <= 0:
            result["status"] = "SKIPPED"
            result["msg"] = "无有效下单数量（可能因阈值/资金/仓位已达目标）"
            return result

        if action == SignalType.BUY:
            success = self.account.buy(
                symbol,
                price,
                qty,
                time,
                reason,
                signal_id,
                factors,
                trade_tag=trade_tag,
            )
            if success:
                result["status"] = "SUCCESS"
                result["quantity"] = qty
                result["msg"] = f"买入成功: {qty}股"
            else:
                if signal_id in self.account.processed_signals:
                    result["status"] = "SKIPPED"
                    result["msg"] = "买入跳过: 信号已处理"
                else:
                    result["status"] = "FAILED"
                    result["msg"] = "买入失败: 资金不足"
            return result

        # SELL
        success = self.account.sell(
            symbol,
            price,
            qty,
            time,
            reason,
            signal_id,
            factors,
            trade_tag=trade_tag,
        )
        if success:
            result["status"] = "SUCCESS"
            result["quantity"] = qty
            result["msg"] = "卖出成功"
        else:
            if signal_id in self.account.processed_signals:
                result["status"] = "SKIPPED"
                result["msg"] = "卖出跳过: 信号已处理"
            else:
                result["status"] = "FAILED"
                result["msg"] = "卖出失败"

        return result

    def _normalize_quantity(self, symbol: str, quantity: int) -> int:
        lot_size = self.lot_sizes.get(symbol, 1)
        if lot_size > 1:
            return (quantity // lot_size) * lot_size
        return quantity

    def _buy(
        self,
        symbol: str,
        time: Any,
        price: float,
        reason: str,
        signal_id: str,
        factors: Dict[str, Any],
        result: Dict[str, Any],
        requested_qty: Any = None,
        trade_tag: Any = None,
    ):
        """执行买入逻辑"""
        current_equity = self.account.get_total_equity()

        if isinstance(requested_qty, (int, float)) and requested_qty > 0:
            quantity = int(requested_qty)
        else:
            quantity = self.position_manager.calculate_buy_quantity(
                total_equity=current_equity,
                available_cash=self.account.cash,
                price=price,
            )

        quantity = self._normalize_quantity(symbol, quantity)

        if quantity > 0:
            success = self.account.buy(
                symbol,
                price,
                quantity,
                time,
                reason,
                signal_id,
                factors,
                trade_tag=trade_tag,
            )
            if success:
                result["status"] = "SUCCESS"
                result["quantity"] = quantity
                result["msg"] = f"买入成功: {quantity}股"
            else:
                if signal_id in self.account.processed_signals:
                    result["status"] = "SKIPPED"
                    result["msg"] = "买入跳过: 信号已处理"
                else:
                    result["status"] = "FAILED"
                    result["msg"] = "买入失败: 资金不足"
        else:
            result["status"] = "SKIPPED"
            result["msg"] = "买入跳过: 计算数量为0"

    def _sell(
        self,
        symbol: str,
        time: Any,
        price: float,
        reason: str,
        signal_id: str,
        factors: Dict[str, Any],
        result: Dict[str, Any],
        requested_qty: Any = None,
        trade_tag: Any = None,
    ):
        """执行卖出逻辑"""
        current_pos = self.account.positions.get(symbol, 0)
        if current_pos <= 0:
            result["status"] = "FAILED"
            result["msg"] = "卖出失败: 无持仓"
            return

        if isinstance(requested_qty, (int, float)) and requested_qty > 0:
            quantity = min(int(requested_qty), current_pos)
        else:
            quantity = current_pos

        quantity = self._normalize_quantity(symbol, quantity)
        if quantity <= 0:
            result["status"] = "SKIPPED"
            result["msg"] = "卖出跳过: 计算数量为0"
            return

        success = self.account.sell(
            symbol,
            price,
            quantity,
            time,
            reason,
            signal_id,
            factors,
            trade_tag=trade_tag,
        )
        if success:
            result["status"] = "SUCCESS"
            result["quantity"] = quantity
            result["msg"] = "卖出成功"
        else:
            if signal_id in self.account.processed_signals:
                result["status"] = "SKIPPED"
                result["msg"] = "卖出跳过: 信号已处理"
            else:
                result["status"] = "FAILED"
                result["msg"] = "卖出失败"
