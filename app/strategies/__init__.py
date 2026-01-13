from typing import Dict, Any, List, Type, cast
import logging
from .strategy import Strategy
from .macd import MACDStrategy
from .rsi import RSIStrategy
from app.core.constants import StraegyName

__all__ = [
    "Strategy",
    "create_strategy",
]

logger = logging.getLogger(__name__)


def create_strategy(name: StraegyName, **kwargs: Any) -> Strategy:
    """Create strategy instance by enum or string.

    This project prefers using enums (e.g. ``TradeStraegy.MACD``) instead of hard-coded strings.
    For compatibility with YAML config, string input is still supported.
    """
    if isinstance(name, StraegyName):
        normalized = name.value
    else:
        normalized = str(name).strip().upper()

    if normalized == StraegyName.COMPOSITE.value:
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
        StraegyName.MACD.value: MACDStrategy,
        StraegyName.RSI.value: RSIStrategy,
        StraegyName.TREND_SWING_T.value: TrendSwingTStrategy,
    }

    cls = mapping.get(normalized)
    if cls is None:
        logger.error(
            f"Strategy '{name}' not found. Defaulting to {StraegyName.MACD.value}."
        )
        cls = MACDStrategy

    return cls(**kwargs)
