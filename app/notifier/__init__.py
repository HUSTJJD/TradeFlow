from app.core import cfg, NotifierType
from .notifier import Notifier
from .email import EmailNotifier

def create_notifier() -> Notifier:
    if cfg.app.notifier_type == NotifierType.EMAIL:
        return EmailNotifier()
    return Notifier()

__all__ = ["create_notifier"]
