
from core import TradeMode
from .engine import Engine
from .backtest import BacktestEngine
from .live import LiveEngine
from .paper import PaperEngine


def create_engine(engine_type: TradeMode) -> Engine:
    """创建执行引擎
	Params:
	
    
	"""
    if engine_type == TradeMode.BACKTEST:
        return BacktestEngine()
    elif engine_type == TradeMode.LIVE:
        return LiveEngine()
    elif engine_type == TradeMode.PAPER:
        return PaperEngine()
    else:
        raise TypeError(f"Invalid TradeMode: {engine_type}")

__all__ = [
    "Engine",
    "create_engine",
]
