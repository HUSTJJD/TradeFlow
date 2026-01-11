from typing import Dict, Any, List, Type
import logging
from .base import Strategy
from .macd import MACDStrategy
from .rsi import RSIStrategy
from .composite import CompositeStrategy
from .trend_swing_t import TrendSwingTStrategy

__all__ = [
    "Strategy",
    "MACDStrategy",
    "RSIStrategy",
    "CompositeStrategy",
    "TrendSwingTStrategy",
]

logger = logging.getLogger(__name__)

STRATEGY_MAP: Dict[str, Type[Strategy]] = {
    "MACD": MACDStrategy,
    "RSI": RSIStrategy,
    "Composite": CompositeStrategy,
    "TrendSwingT": TrendSwingTStrategy,
}


def get_strategy(name: str, **kwargs: Any) -> Strategy:
    """
    Factory function to get a strategy instance by name.

    Args:
        name: Name of the strategy (e.g., 'MACD', 'RSI', 'Composite').
        **kwargs: Arguments to pass to the strategy constructor.

    Returns:
        An instance of the requested strategy.
    """
    if name == "Composite":
        # Special handling for CompositeStrategy
        sub_strategies_config = kwargs.get("strategies", [])
        mode = kwargs.get("mode", "consensus")

        sub_strategies: List[Strategy] = []
        for sub_conf in sub_strategies_config:
            sub_name = sub_conf.get("name")
            sub_params = sub_conf.get("params", {})
            if sub_name:
                try:
                    sub_strategy = get_strategy(sub_name, **sub_params)
                    sub_strategies.append(sub_strategy)
                except Exception as e:
                    logger.error(f"Failed to load sub-strategy {sub_name}: {e}")

        return CompositeStrategy(strategies=sub_strategies, mode=mode)

    strategy_class = STRATEGY_MAP.get(name)
    if not strategy_class:
        logger.error(f"Strategy '{name}' not found. Defaulting to MACDStrategy.")
        return MACDStrategy(**kwargs)

    try:
        return strategy_class(**kwargs)
    except Exception as e:
        logger.error(f"Failed to initialize strategy {name}: {e}")
        raise
