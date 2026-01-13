from abc import ABC, abstractmethod
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class Provider(ABC):
    """券商API 抽象基类，定义统一的数据访问接口。"""

    @abstractmethod
    def request_buy(self, symbol: str, quantity: int, callback: Callable) -> None:
        """买入股票"""
        pass

    @abstractmethod
    def request_sell(self, symbol: str, quantity: int, callback: Callable) -> None:
        """卖出股票"""
        pass
