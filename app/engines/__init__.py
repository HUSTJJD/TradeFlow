from longport.openapi import QuoteContext
from app.core.constants import TradeMode
from app.strategies import Strategy
from .engine import Engine, BacktestEngine, LiveEngine

__all__ = [
    "Engine",
    "create_engine",
]


def create_engine(engine_type: TradeMode, quote_ctx: QuoteContext, strategy: Strategy) -> Engine:
    """Create engine instance by TradeMode.

    Keep it minimal: no registry/manager; just a small enum switch.
    """
    if engine_type == TradeMode.BACKTEST:
        return BacktestEngine(quote_ctx=quote_ctx, strategy=strategy)
    if engine_type in (TradeMode.LIVE, TradeMode.PAPER):
        # PAPER is treated as LIVE execution with a paper account.
        return LiveEngine(quote_ctx=quote_ctx, strategy=strategy)

    raise ValueError(f"Invalid engine type: {engine_type}")
