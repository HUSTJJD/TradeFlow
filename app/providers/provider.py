from abc import ABC, abstractmethod
from app.core import cfg, singleton_threadsafe, MarketType
from typing import Dict, Any, List, Optional
from datetime import date, timedelta
import pandas as pd
import logging
import os
import requests
from app.utils.market import get_market_symbols

logger = logging.getLogger(__name__)


STACK_DB_PATH = os.path.join("data", "stacks.json")


class Provider(ABC):
    """券商API 抽象基类，定义统一的数据访问接口。"""

    def __init__(self):
        self._session = None

    def pull_stack_list(self) -> bool:
        """拉取数据"""
        try:
            markets = cfg.markets
            for market in markets:
                self.get_universe_symbols(market)

            self._session = requests.Session()
            self._session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "*/*",
                }
            )
            self._initialized = True
            logger.info("数据提供器初始化完成")
            return True
        except Exception as e:
            logger.error(f"初始化数据提供器失败: {e}")
            return False

    @abstractmethod
    def get_data(self, symbol: str, **kwargs: Any) -> Optional[pd.DataFrame]:
        """获取指定标的的数据"""
        pass

    @abstractmethod
    def get_multiple_data(
        self, symbols: List[str], **kwargs: Any
    ) -> Dict[str, pd.DataFrame]:
        """批量获取多个标的的数据"""
        pass

    @abstractmethod
    def get_stock_names(self, symbols: List[str]) -> Dict[str, str]:
        """获取股票名称"""
        pass

    @abstractmethod
    def get_stock_lot_sizes(self, symbols: List[str]) -> Dict[str, int]:
        """获取股票最小交易单位"""
        pass

    @abstractmethod
    def get_benchmark_returns(
        self, start_date: date, end_date: date
    ) -> Dict[str, float]:
        """获取基准收益率"""
        pass

    def get_universe_symbols(self, market: str, **kwargs: Any) -> List[Dict[str, Any]]:
        """获取指定市场的标的清单"""
        try:
            df = get_market_symbols()
            
            market_upper = market.upper()
            
            if market_upper == "CN":
                # A股包括 SH, SZ, BJ
                filtered_df = df[df["market"].isin(["SH", "SZ", "BJ"])]
            elif market_upper == "HK":
                filtered_df = df[df["market"] == "HK"]
            # 支持按板块过滤 (使用新的 Market 枚举值)
            elif market in [m.value for m in MarketType]:
                filtered_df = df[df["board"] == market]
            # 兼容旧的枚举值字符串
            elif market_upper in ["SSE_MAIN", "SZSE_MAIN"]:
                filtered_df = df[df["board"] == MarketType.MAIN.value]
            elif market_upper == "SSE_STAR":
                filtered_df = df[df["board"] == MarketType.STAR.value]
            elif market_upper == "SZSE_GEM":
                filtered_df = df[df["board"] == MarketType.CHINEXT.value]
            else:
                logger.warning(f"未知的市场类型: {market}，返回空列表")
                return []
            
            return filtered_df[["symbol", "name"]].to_dict("records")
        except Exception as e:
            logger.error(f"获取 {market} 标的清单失败: {e}")
            return []
