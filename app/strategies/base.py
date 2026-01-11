import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Union
import pandas as pd

logger = logging.getLogger(__name__)


class Strategy(ABC):
    """
    所有交易策略的抽象基类。
    """

    def __init__(self) -> None:
        pass

    @abstractmethod
    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        分析市场数据并生成交易信号。

        Args:
            symbol: 股票代码（例如 '700.HK'）。
            df: 包含至少 'close' 列的 K 线数据 DataFrame。

        Returns:
            包含信号的字典:
            {
                'action': 'BUY' | 'SELL' | 'HOLD',
                'price': float,
                'reason': str
            }
        """
        pass
