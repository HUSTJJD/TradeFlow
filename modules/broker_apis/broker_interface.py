"""券商API接口基类
定义统一的券商API接口规范
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime


class Market(Enum):
    """市场枚举"""
    HK = "HK"  # 香港市场
    US = "US"  # 美国市场
    CN = "CN"  # 中国大陆市场


class ProductType(Enum):
    """产品类型枚举"""
    STOCK = "stock"  # 股票
    ETF = "etf"  # ETF
    WARRANT = "warrant"  # 窝轮
    CBBC = "cbbc"  # 牛熊证
    OPTION = "option"  # 期权


class OrderSide(Enum):
    """订单方向枚举"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """订单类型枚举"""
    MARKET = "MARKET"  # 市价单
    LIMIT = "LIMIT"    # 限价单
    STOP = "STOP"      # 止损单


class BrokerInterface(ABC):
    """券商API接口基类"""
    
    def __init__(self, broker_name: str, config: Dict[str, Any]):
        self.broker_name = broker_name
        self.config = config
        self.is_connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """连接券商API"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """断开券商API连接"""
        pass
    
    @abstractmethod
    def get_account_balance(self) -> Dict[str, Any]:
        """获取账户余额信息"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """获取持仓信息"""
        pass
    
    @abstractmethod
    def submit_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                    quantity: int, price: Optional[float] = None) -> Dict[str, Any]:
        """提交订单"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态"""
        pass
    
    @abstractmethod
    def get_market_data(self, symbol: str, data_type: str) -> Dict[str, Any]:
        """获取市场数据"""
        pass
    
    @abstractmethod
    def get_historical_data(self, symbol: str, period: str, 
                           start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """获取历史数据"""
        pass
    
    @abstractmethod
    def get_supported_markets(self) -> List[Market]:
        """获取支持的交易市场"""
        pass
    
    @abstractmethod
    def get_supported_products(self) -> List[ProductType]:
        """获取支持的产品类型"""
        pass
    
    @abstractmethod
    def get_trading_hours(self, market: Market) -> Dict[str, str]:
        """获取交易时间"""
        pass
    
    def validate_connection(self) -> Dict[str, Any]:
        """验证连接状态"""
        return {
            "broker_name": self.broker_name,
            "is_connected": self.is_connected,
            "supported_markets": [market.value for market in self.get_supported_markets()],
            "supported_products": [product.value for product in self.get_supported_products()],
            "timestamp": datetime.now().isoformat()
        }
    
    def get_broker_info(self) -> Dict[str, Any]:
        """获取券商信息"""
        return {
            "broker_name": self.broker_name,
            "description": self.config.get("description", ""),
            "commission_rate": self.config.get("commission_rate", 0.001),
            "min_commission": self.config.get("min_commission", 0),
            "supported_features": self.config.get("supported_features", []),
            "api_version": self.config.get("api_version", "1.0")
        }