from app.core import cfg, ProviderName
from .provider import Provider
from .longport import LongPortProvider


def create_provider() -> Provider:
    provider_name = cfg.get()
    if provider_name == ProviderName.LONGPORT:
        return LongPortProvider()
    else:
        raise ValueError(f"Unknown provider: {provider_name}")


__all__ = ["Provider", "create_provider"]
