from app.core import global_config, ProviderType
from .provider import Provider
from .longport import LongPortProvider


def create_provider() -> Provider:
    provider_name = global_config.get()
    if provider_name == ProviderType.LONGPORT:
        return LongPortProvider()
    else:
        raise ValueError(f"Unknown provider: {provider_name}")


__all__ = ["Provider", "create_provider"]
