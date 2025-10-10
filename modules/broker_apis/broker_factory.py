"""券商工厂类
负责创建和管理不同券商的API实例
"""

from typing import Dict, Any, Optional
from .broker_interface import BrokerInterface, Market
from .brokers.longport_broker import LongPortBroker
from .brokers.ibkr_broker import IBKRBroker
from .brokers.qmt_broker import QMTBroker


class BrokerFactory:
    """券商工厂类"""
    
    # 券商类型映射（统一使用小写键名）
    BROKER_MAPPING = {
        "longport": LongPortBroker,  # 修复：统一使用小写
        "ibkr": IBKRBroker,
        "qmt": QMTBroker,
    }
    
    # 市场与券商映射（自动选择逻辑）
    MARKET_BROKER_MAPPING = {
        Market.HK: ["longport"],      # 港股首选长桥（修复：使用小写）
        Market.US: ["ibkr", "longport"],  # 美股首选IBKR，备选长桥（修复：使用小写）
        Market.CN: ["qmt"]  # A股支持多种券商
    }
    
    @classmethod
    def create_broker(cls, broker_type: str, config: Dict[str, Any]) -> Optional[BrokerInterface]:
        """创建指定类型的券商API实例"""
        broker_class = cls.BROKER_MAPPING.get(broker_type.lower())  # 修复：使用小写匹配
        if not broker_class:
            raise ValueError(f"不支持的券商类型: {broker_type}")
        
        return broker_class(config)
    
    @classmethod
    def get_available_brokers_for_market(cls, market: Market) -> list:
        """获取指定市场可用的券商列表"""
        return cls.MARKET_BROKER_MAPPING.get(market, [])
    
    @classmethod
    def get_best_broker_for_market(cls, market: Market, broker_configs: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """为指定市场选择最优券商"""
        available_brokers = cls.get_available_brokers_for_market(market)
        
        for broker_type in available_brokers:
            broker_config = broker_configs.get(broker_type)
            if broker_config and broker_config.get("enabled", False):
                return broker_type
        
        return None
    
    @classmethod
    def get_all_supported_brokers(cls) -> list:
        """获取所有支持的券商类型"""
        return list(cls.BROKER_MAPPING.keys())
    
    @classmethod
    def validate_broker_config(cls, broker_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证券商配置"""
        errors = []
        warnings = []
        
        # 基本配置验证
        required_fields = ["enabled", "description"]
        for field in required_fields:
            if field not in config:
                errors.append(f"缺少必需字段: {field}")
        
        # 券商特定配置验证（统一使用小写比较）
        broker_type_lower = broker_type.lower()
        
        if broker_type_lower == "longport":  # 修复：使用小写比较
            required_api_fields = ["app_key", "app_secret", "access_token"]
            for field in required_api_fields:
                if not config.get(field):
                    errors.append(f"长桥API缺少必需字段: {field}")
        
        elif broker_type_lower == "ibkr":
            if not config.get("host") or not config.get("port"):
                errors.append("IBKR API需要配置host和port")
        
        elif broker_type_lower == "qmt":
            if not config.get("account_id"):
                errors.append(f"{broker_type.upper()}需要配置account_id")
        
        # 检查连接性（可选）
        if config.get("test_connection", False):
            try:
                broker = cls.create_broker(broker_type, config)
                if broker:
                    connection_result = broker.validate_connection()
                    if not connection_result.get("is_connected", False):
                        warnings.append(f"{broker_type}连接测试失败")
            except Exception as e:
                warnings.append(f"{broker_type}连接测试异常: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "broker_type": broker_type
        }
    
    @classmethod
    def get_broker_capabilities(cls, broker_type: str) -> Dict[str, Any]:
        """获取券商能力信息"""
        capabilities = {
            "LongPort": {
                "supported_markets": ["HK", "US"],
                "supported_products": ["stock", "etf", "warrant", "cbbc"],
                "features": ["real_time_data", "historical_data", "trading", "portfolio"],
                "rate_limits": {
                    "quote": "10次/秒，最大5并发",
                    "trade": "30次/30秒"
                }
            },
            "ibkr": {
                "supported_markets": ["US", "HK", "CN", "EU"],
                "supported_products": ["stock", "etf", "option", "future"],
                "features": ["real_time_data", "historical_data", "trading", "portfolio", "options_chain"],
                "rate_limits": {
                    "quote": "50次/秒",
                    "trade": "无限制（需遵守交易所规则）"
                }
            },
            "qmt": {
                "supported_markets": ["CN"],
                "supported_products": ["stock", "etf"],
                "features": ["real_time_data", "historical_data", "trading", "quant_strategy"],
                "rate_limits": {
                    "quote": "依赖券商限制",
                    "trade": "依赖券商限制"
                }
            }
        }
        
        return capabilities.get(broker_type, {})