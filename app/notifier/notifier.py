from abc import ABC, abstractmethod
from core import singleton_threadsafe

@singleton_threadsafe
class Notifier(ABC):
    def __init__(self):
        pass
    @abstractmethod
    def notify(self, title: str, content: str):
        raise NotImplementedError()
