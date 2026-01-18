from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import logging
from longport.openapi import QuoteContext, Period
from app.core import cfg, ActionType, TradeMode
from app.strategies import Strategy
from app.trading import create_account
from app.providers import create_provider
from app.utils import update_market_symbols, update_stock_datas

logger = logging.getLogger(__name__)


class Engine(ABC):
    """策略执行引擎抽象基类，定义统一的策略执行接口。"""

    def __init__(self):
        # 初始化数据提供器
        self.provider = create_provider()
        self.account = create_account()

    def run(self):
        """运行策略执行引擎"""
        self.update_market_data()
    
    def update_market_data(self) -> None:
        update_market_symbols()
        update_stock_datas()