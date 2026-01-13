from app.core import global_config, NotifierType
from .notifier import Notifier
from .email import EmailNotifier

def create_notifier() -> Notifier:
    if global_config.notifier_type == NotifierType.EMAIL:
        return EmailNotifier()
    return Notifier()

__all__ = ["create_notifier"]
