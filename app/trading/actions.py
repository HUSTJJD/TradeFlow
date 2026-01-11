from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.core.constants import SignalType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TradeActionContext:
    signal_id: str
    symbol: str
    timestamp: Any
    price: float
    reason: str
    factors: Dict[str, Any]
    trade_tag: Optional[str]


class TradeActionHandler(ABC):
    @abstractmethod
    def can_handle(self, action: Any) -> bool:
        raise NotImplementedError

    @abstractmethod
    def execute(self, manager: Any, ctx: TradeActionContext) -> Dict[str, Any]:
        raise NotImplementedError


class BuyActionHandler(TradeActionHandler):
    def can_handle(self, action: Any) -> bool:
        return action == SignalType.BUY

    def execute(self, manager: Any, ctx: TradeActionContext) -> Dict[str, Any]:
        return manager._execute_buy(
            ctx.signal_id,
            ctx.symbol,
            ctx.timestamp,
            ctx.price,
            ctx.reason,
            ctx.factors,
            ctx.trade_tag,
        )


class SellActionHandler(TradeActionHandler):
    def can_handle(self, action: Any) -> bool:
        return action == SignalType.SELL

    def execute(self, manager: Any, ctx: TradeActionContext) -> Dict[str, Any]:
        return manager._execute_sell(
            ctx.signal_id,
            ctx.symbol,
            ctx.timestamp,
            ctx.price,
            ctx.reason,
            ctx.factors,
            ctx.trade_tag,
        )


class DefaultNoopActionHandler(TradeActionHandler):
    def can_handle(self, action: Any) -> bool:
        return True

    def execute(self, manager: Any, ctx: TradeActionContext) -> Dict[str, Any]:
        return {
            "status": "SKIPPED",
            "action": ctx.factors.get("action", None),
            "symbol": ctx.symbol,
            "price": ctx.price,
            "time": ctx.timestamp,
            "quantity": 0,
            "msg": "无交易动作",
            "signal_id": ctx.signal_id,
        }


class TradeActionRegistry:
    def __init__(self) -> None:
        self._handlers: list[TradeActionHandler] = [
            BuyActionHandler(),
            SellActionHandler(),
            DefaultNoopActionHandler(),
        ]

    def dispatch(self, manager: Any, ctx: TradeActionContext, action: Any) -> Dict[str, Any]:
        for handler in self._handlers:
            if handler.can_handle(action):
                return handler.execute(manager, ctx)

        return {
            "status": "SKIPPED",
            "action": action,
            "symbol": ctx.symbol,
            "price": ctx.price,
            "time": ctx.timestamp,
            "quantity": 0,
            "msg": "未找到处理器",
            "signal_id": ctx.signal_id,
        }
