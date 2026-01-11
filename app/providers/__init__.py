from .provider import Provider
from app.core.constants import ProviderType, TradeMode
__all__ = [
    "provider",
    "provider_factory"
]

def create_provider(provider_name: str, trade_mode: TradeMode) -> Provider:
    if provider_name == ProviderType.LONGPORT:
        from .longport import LongPortProvider
        return LongPortProvider()
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
    