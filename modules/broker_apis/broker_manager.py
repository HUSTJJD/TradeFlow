"""券商管理器
负责多券商API的统一管理和自动选择
"""

from typing import Dict, Any, List, Optional
from .broker_interface import BrokerInterface, Market, ProductType, OrderSide, OrderType
from .broker_factory import BrokerFactory


class BrokerManager:
    """券商管理器"""
    
    def __init__(self, broker_configs: Dict[str, Dict[str, Any]]):
        self.broker_configs = broker_configs
        self.active_brokers: Dict[str, BrokerInterface] = {}
        self.market_broker_mapping: Dict[Market, str] = {}
        self._initialize_brokers()
    
    def _initialize_brokers(self):
        """初始化券商连接"""
        for broker_type, config in self.broker_configs.items():
            if config.get("enabled", False):
                try:
                    broker = BrokerFactory.create_broker(broker_type, config)
                    if broker and broker.connect():
                        self.active_brokers[broker_type] = broker
                        print(f"券商 {broker_type} 连接成功")
                except Exception as e:
                    print(f"券商 {broker_type} 连接失败: {e}")
        
        # 建立市场与券商映射
        self._build_market_broker_mapping()
    
    def _build_market_broker_mapping(self):
        """建立市场与券商映射关系"""
        for market in Market:
            best_broker = BrokerFactory.get_best_broker_for_market(market, self.broker_configs)
            if best_broker and best_broker in self.active_brokers:
                self.market_broker_mapping[market] = best_broker
                print(f"市场 {market.value} 使用券商: {best_broker}")
    
    def get_broker_for_market(self, market: Market) -> Optional[BrokerInterface]:
        """获取指定市场的券商实例"""
        broker_type = self.market_broker_mapping.get(market)
        if broker_type:
            return self.active_brokers.get(broker_type)
        return None
    
    def get_broker_for_symbol(self, symbol: str) -> Optional[BrokerInterface]:
        """根据标的符号获取券商实例"""
        # 简单实现：根据符号前缀判断市场
        market = self._infer_market_from_symbol(symbol)
        if market:
            return self.get_broker_for_market(market)
        return None
    
    def _infer_market_from_symbol(self, symbol: str) -> Optional[Market]:
        """根据符号推断市场"""
        symbol_upper = symbol.upper()
        
        if symbol_upper.startswith(('0', '3', '6')) and len(symbol) == 6:
            return Market.CN  # A股
        elif symbol_upper.startswith(('00', '30', '60')) and len(symbol) == 6:
            return Market.CN  # A股
        elif symbol_upper.endswith('.HK'):
            return Market.HK  # 港股
        elif symbol_upper.endswith('.US') or (symbol_upper.isalpha() and len(symbol) <= 5):
            return Market.US  # 美股
        elif symbol_upper.endswith('.SH') or symbol_upper.endswith('.SZ'):
            return Market.CN  # A股
        
        return None
    
    def submit_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                    quantity: int, price: Optional[float] = None) -> Dict[str, Any]:
        """提交订单（自动选择券商）"""
        broker = self.get_broker_for_symbol(symbol)
        if not broker:
            return {"success": False, "reason": f"未找到支持标的 {symbol} 的券商"}
        
        return broker.submit_order(symbol, side, order_type, quantity, price)
    
    def get_account_balance(self, broker_type: Optional[str] = None) -> Dict[str, Any]:
        """获取账户余额信息"""
        if broker_type:
            broker = self.active_brokers.get(broker_type)
            if broker:
                return broker.get_account_balance()
            return {}
        
        # 返回所有活跃券商的账户余额
        all_balances = {}
        for broker_type, broker in self.active_brokers.items():
            balance = broker.get_account_balance()
            if balance:
                all_balances[broker_type] = balance
        
        return all_balances
    
    def get_positions(self, broker_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取持仓信息"""
        if broker_type:
            broker = self.active_brokers.get(broker_type)
            if broker:
                return broker.get_positions()
            return []
        
        # 返回所有活跃券商的持仓
        all_positions = []
        for broker in self.active_brokers.values():
            positions = broker.get_positions()
            all_positions.extend(positions)
        
        return all_positions
    
    def get_market_data(self, symbol: str, data_type: str) -> Dict[str, Any]:
        """获取市场数据"""
        broker = self.get_broker_for_symbol(symbol)
        if broker:
            return broker.get_market_data(symbol, data_type)
        return {}
    
    def get_historical_data(self, symbol: str, period: str, 
                           start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """获取历史数据"""
        broker = self.get_broker_for_symbol(symbol)
        if broker:
            return broker.get_historical_data(symbol, period, start_date, end_date)
        return []
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            "total_brokers": len(self.active_brokers),
            "active_brokers": list(self.active_brokers.keys()),
            "market_mapping": {
                market.value: broker_type 
                for market, broker_type in self.market_broker_mapping.items()
            },
            "broker_status": {}
        }
        
        for broker_type, broker in self.active_brokers.items():
            status["broker_status"][broker_type] = broker.validate_connection()
        
        return status
    
    def reconnect_broker(self, broker_type: str) -> bool:
        """重新连接指定券商"""
        if broker_type in self.active_brokers:
            try:
                broker = self.active_brokers[broker_type]
                if broker.disconnect() and broker.connect():
                    return True
            except Exception as e:
                print(f"重新连接券商 {broker_type} 失败: {e}")
        
        return False
    
    def add_broker(self, broker_type: str, config: Dict[str, Any]) -> bool:
        """添加新的券商"""
        if broker_type in self.active_brokers:
            print(f"券商 {broker_type} 已存在")
            return False
        
        try:
            broker = BrokerFactory.create_broker(broker_type, config)
            if broker and broker.connect():
                self.active_brokers[broker_type] = broker
                self.broker_configs[broker_type] = config
                self._build_market_broker_mapping()  # 重新建立映射
                return True
        except Exception as e:
            print(f"添加券商 {broker_type} 失败: {e}")
        
        return False
    
    def remove_broker(self, broker_type: str) -> bool:
        """移除券商"""
        if broker_type in self.active_brokers:
            try:
                broker = self.active_brokers[broker_type]
                broker.disconnect()
                del self.active_brokers[broker_type]
                del self.broker_configs[broker_type]
                self._build_market_broker_mapping()  # 重新建立映射
                return True
            except Exception as e:
                print(f"移除券商 {broker_type} 失败: {e}")
        
        return False
    
    def validate_all_brokers(self) -> Dict[str, Any]:
        """验证所有券商配置"""
        results = {}
        for broker_type, config in self.broker_configs.items():
            results[broker_type] = BrokerFactory.validate_broker_config(broker_type, config)
        
        return results