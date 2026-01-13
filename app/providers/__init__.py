from app.core import cfg, ProviderName
from .provider import Provider
from .longport import LongPortProvider


def create_provider() -> Provider:
    provider = cfg.app.using_provider
    if provider == ProviderName.LONGPORT:
        return LongPortProvider()
    else:
        raise ValueError(f"Unknown provider: {provider}")


__all__ = ["Provider", "create_provider"]
