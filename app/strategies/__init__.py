from typing import Dict, Any, List, Type, cast
import logging
from .strategy import Strategy
from .macd import MACDStrategy
from .rsi import RSIStrategy
from .composite import CompositeStrategy
from .trend_swing_t import TrendSwingTStrategy
from app.core.constants import TradeStraegy

__all__ = [
    "Strategy",
    "create_strategy",
]

logger = logging.getLogger(__name__)


def create_strategy(name: TradeStraegy | str, **kwargs: Any) -> Strategy:
    """Create strategy instance by enum or string.

    This project prefers using enums (e.g. ``TradeStraegy.MACD``) instead of hard-coded strings.
    For compatibility with YAML config, string input is still supported.
    """
    if isinstance(name, TradeStraegy):
        normalized = name.value
    else:
        normalized = str(name).strip().upper()

    if normalized == TradeStraegy.COMPOSITE.value:
        sub_strategies_config = kwargs.get("strategies", [])
        mode = kwargs.get("mode", "consensus")

        sub_strategies: List[Strategy] = []
        for sub_conf in sub_strategies_config:
            sub_name = cast(str, sub_conf.get("name") or "")
            sub_params = cast(Dict[str, Any], sub_conf.get("params") or {})
            if not sub_name:
                continue
            try:
                sub_strategies.append(create_strategy(sub_name, **sub_params))
            except Exception as e:
                logger.error(f"Failed to load sub-strategy {sub_name}: {e}")

        return CompositeStrategy(strategies=sub_strategies, mode=mode)

    mapping: Dict[str, Type[Strategy]] = {
        TradeStraegy.MACD.value: MACDStrategy,
        TradeStraegy.RSI.value: RSIStrategy,
        TradeStraegy.TREND_SWING_T.value: TrendSwingTStrategy,
    }

    cls = mapping.get(normalized)
    if cls is None:
        logger.error(
            f"Strategy '{name}' not found. Defaulting to {TradeStraegy.MACD.value}."
        )
        cls = MACDStrategy

    return cls(**kwargs)
