from abc import ABC, abstractmethod

class Notifier(ABC):
    def __init__(self):
        pass
    @abstractmethod
    def notify(self, title: str, content: str) -> None:
        raise NotImplementedError()
