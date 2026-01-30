from abc import ABC, abstractmethod
from datetime import date
import logging
from typing import Callable
import pandas as pd

from app.core import TIME_FORMAT

logger = logging.getLogger(__name__)


class Provider(ABC):
    """券商API 抽象基类，定义统一的数据访问接口。"""

    def __init__(self):
        pass

    @abstractmethod
    def request_buy(self, symbol: str, quantity: int, callback: Callable) -> None:
        """买入股票"""
        pass

    @abstractmethod
    def request_sell(self, symbol: str, quantity: int, callback: Callable) -> None:
        """卖出股票"""
        pass

    @abstractmethod
    def convert_a_symbol(self, symbol: str) -> str:
        """转换A股代码"""
        pass

    @abstractmethod
    def convert_hk_symbol(self, symbol: str) -> str:
        """转换H股代码"""
        pass

    @abstractmethod
    def request_static_info(self, symbols: list[str]) -> pd.DataFrame:
        """获取静态信息"""
        pass

    @abstractmethod
    def request_history_info(
        self,
        symbol: str,
        start_date: str,
        end_date: str = date.today().strftime(TIME_FORMAT),
    ) -> pd.DataFrame:
        """获取历史信息"""
        pass
