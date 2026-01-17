from abc import ABC, abstractmethod
from typing import Dict, Any, Union, Optional
import pandas as pd
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


class Strategy(ABC):
    """
    所有交易策略的抽象基类。
    提供统一的策略接口和生命周期管理。
    """

    def __init__(self):
        """
        初始化策略。
        子类应调用 super().__init__() 以确保正确初始化。
        """