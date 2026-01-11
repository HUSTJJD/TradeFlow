import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.constants import SignalType
from app.trading.account import PaperAccount
from app.trading.position import PositionManager
from app.trading.actions import TradeActionContext, TradeActionRegistry

logger = logging.getLogger(__name__)


class TradeManager:
    """
    统一交易管理器，负责协调账户管理、仓位管理和交易执行。
    简化职责边界：
    - Account: 只负责资金和持仓的存储、计算
    - PositionManager: 只负责仓位计算和风险控制
    - TradeManager: 统一协调交易流程和信号处理
    """

    def __init__(
        self,
        account: PaperAccount,
        position_manager: PositionManager,
        lot_sizes: Optional[Dict[str, int]] = None,
    ):
        self.account = account
        self.position_manager = position_manager
        self.lot_sizes = lot_sizes or {}

        self._action_registry = TradeActionRegistry()

        # 信号处理状态
        self.processed_signals: set = set()

    def set_lot_sizes(self, lot_sizes: Dict[str, int]) -> None:
        """设置股票最小交易单位"""
        self.lot_sizes = lot_sizes

    def execute_trade(
        self,
        signal: Dict[str, Any],
        symbol: str,
        timestamp: datetime,
        price: float,
    ) -> Dict[str, Any]:
        """执行交易信号，统一处理买入和卖出逻辑。"""
        action = signal.get("action")
        reason = str(signal.get("reason", ""))
        factors = signal.get("factors", {})
        if not isinstance(factors, dict):
            factors = {}
        trade_tag = signal.get("trade_tag")

        signal_id = f"{symbol}_{timestamp.strftime('%Y%m%d%H%M%S')}_{action}"

        if signal_id in self.processed_signals:
            return {
                "status": "SKIPPED",
                "action": action,
                "symbol": symbol,
                "price": price,
                "time": timestamp,
                "quantity": 0,
                "msg": "信号已处理",
                "signal_id": signal_id,
            }

        self.account.update_price(symbol, price)

        ctx = TradeActionContext(
            signal_id=signal_id,
            symbol=symbol,
            timestamp=timestamp,
            price=price,
            reason=reason,
            factors=factors,
            trade_tag=trade_tag,
        )
        return self._action_registry.dispatch(self, ctx, action)
    
    def _execute_buy(
        self,
        signal_id: str,
        symbol: str,
        timestamp: datetime,
        price: float,
        reason: str,
        factors: Dict[str, Any],
        trade_tag: Optional[str],
    ) -> Dict[str, Any]:
        """执行买入交易"""
        # 计算买入数量
        lot_size = self.lot_sizes.get(symbol, 1)
        current_equity = self.account.get_total_equity()
        current_position = self.account.positions.get(symbol, 0)
        
        quantity = self.position_manager.calculate_order_quantity(
            action=SignalType.BUY,
            current_position=current_position,
            price=price,
            total_equity=current_equity,
            available_cash=self.account.cash,
            lot_size=lot_size,
            signal={"trade_tag": trade_tag, **factors},
        )
        
        # 数量标准化
        quantity = self._normalize_quantity(symbol, quantity)
        
        if quantity <= 0:
            return {
                "status": "SKIPPED",
                "action": SignalType.BUY,
                "symbol": symbol,
                "price": price,
                "time": timestamp,
                "quantity": 0,
                "msg": "计算数量为0",
                "signal_id": signal_id,
            }
        
        # 执行买入
        success = self.account.buy(
            symbol=symbol,
            price=price,
            quantity=quantity,
            time=timestamp,
            reason=reason,
            signal_id=signal_id,
            factors=factors,
            trade_tag=trade_tag,
        )
        
        if success:
            self.processed_signals.add(signal_id)
            return {
                "status": "SUCCESS",
                "action": SignalType.BUY,
                "symbol": symbol,
                "price": price,
                "time": timestamp,
                "quantity": quantity,
                "msg": f"买入成功: {quantity}股",
                "signal_id": signal_id,
            }
        else:
            return {
                "status": "FAILED",
                "action": SignalType.BUY,
                "symbol": symbol,
                "price": price,
                "time": timestamp,
                "quantity": 0,
                "msg": "买入失败: 资金不足",
                "signal_id": signal_id,
            }
    
    def _execute_sell(
        self,
        signal_id: str,
        symbol: str,
        timestamp: datetime,
        price: float,
        reason: str,
        factors: Dict[str, Any],
        trade_tag: Optional[str],
    ) -> Dict[str, Any]:
        """执行卖出交易"""
        # 检查当前持仓
        current_position = self.account.positions.get(symbol, 0)
        if current_position <= 0:
            return {
                "status": "FAILED",
                "action": SignalType.SELL,
                "symbol": symbol,
                "price": price,
                "time": timestamp,
                "quantity": 0,
                "msg": "无持仓",
                "signal_id": signal_id,
            }
        
        # 计算卖出数量
        lot_size = self.lot_sizes.get(symbol, 1)
        current_equity = self.account.get_total_equity()
        
        quantity = self.position_manager.calculate_order_quantity(
            action=SignalType.SELL,
            current_position=current_position,
            price=price,
            total_equity=current_equity,
            available_cash=self.account.cash,
            lot_size=lot_size,
            signal={"trade_tag": trade_tag, **factors},
        )
        
        # 数量标准化
        quantity = self._normalize_quantity(symbol, quantity)
        
        if quantity <= 0:
            return {
                "status": "SKIPPED",
                "action": SignalType.SELL,
                "symbol": symbol,
                "price": price,
                "time": timestamp,
                "quantity": 0,
                "msg": "计算数量为0",
                "signal_id": signal_id,
            }
        
        # 执行卖出
        success = self.account.sell(
            symbol=symbol,
            price=price,
            quantity=quantity,
            time=timestamp,
            reason=reason,
            signal_id=signal_id,
            factors=factors,
            trade_tag=trade_tag,
        )
        
        if success:
            self.processed_signals.add(signal_id)
            return {
                "status": "SUCCESS",
                "action": SignalType.SELL,
                "symbol": symbol,
                "price": price,
                "time": timestamp,
                "quantity": quantity,
                "msg": f"卖出成功: {quantity}股",
                "signal_id": signal_id,
            }
        else:
            return {
                "status": "FAILED",
                "action": SignalType.SELL,
                "symbol": symbol,
                "price": price,
                "time": timestamp,
                "quantity": 0,
                "msg": "卖出失败",
                "signal_id": signal_id,
            }
    
    def _normalize_quantity(self, symbol: str, quantity: int) -> int:
        """数量标准化（按最小交易单位）"""
        lot_size = self.lot_sizes.get(symbol, 1)
        if lot_size > 1:
            return (quantity // lot_size) * lot_size
        return quantity
    
    def get_trade_stats(self) -> Dict[str, Any]:
        """获取交易统计信息"""
        return self.account.get_trade_stats()
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        return {
            "cash": self.account.cash,
            "total_equity": self.account.get_total_equity(),
            "positions": self.account.positions,
            "initial_capital": self.account.initial_capital,
            "commission_rate": self.account.commission_rate,
        }
    
    def get_position_suggestion(
        self, signal: Dict[str, Any], current_price: float, total_equity: float
    ) -> str:
        """获取仓位建议"""
        return self.position_manager.get_position_suggestion(signal, current_price, total_equity)
    
    def clear_processed_signals(self) -> None:
        """清空已处理的信号记录"""
        self.processed_signals.clear()
    
    def get_processed_signals_count(self) -> int:
        """获取已处理信号数量"""
        return len(self.processed_signals)