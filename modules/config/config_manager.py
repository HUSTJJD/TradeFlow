"""配置管理模块
管理多市场、多产品、多券商的配置信息
"""

import yaml
from typing import Dict, Any, List, Optional
from enum import Enum
from ..utils.common_utils import Logger


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


class BrokerType(Enum):
    """券商类型枚举"""
    LongPort = "longport"  # 长桥
    IBKR = "ibkr"              # Interactive Brokers
    QMT = "qmt"                # QMT


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.logger = Logger("config_manager")
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.logger.info(f"配置文件加载成功: {self.config_path}")
            return config
            
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        except Exception as e:
            raise Exception(f"配置文件加载失败: {e}")
    
    def get_broker_config(self, broker_type: str) -> Dict[str, Any]:
        """获取券商配置"""
        return self.config["brokers"].get(broker_type, {})
    
    def get_all_broker_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有券商配置"""
        return self.config["brokers"]
    
    def get_market_broker_mapping(self) -> Dict[str, str]:
        """获取市场与券商映射"""
        return self.config["market_broker_mapping"]
    
    def get_broker_for_market(self, market: Market) -> Optional[str]:
        """获取指定市场的默认券商"""
        return self.config["market_broker_mapping"].get(market.value)
    
    def is_broker_enabled(self, broker_type: str) -> bool:
        """检查券商是否启用"""
        broker_config = self.get_broker_config(broker_type)
        return broker_config.get("enabled", False)
    
    def enable_broker(self, broker_type: str, enabled: bool = True):
        """启用或禁用券商"""
        if broker_type not in self.config["brokers"]:
            self.config["brokers"][broker_type] = {}
        
        self.config["brokers"][broker_type]["enabled"] = enabled
        self.update_config({})
    
    def set_market_broker_mapping(self, market: Market, broker_type: str):
        """设置市场与券商映射"""
        self.config["market_broker_mapping"][market.value] = broker_type
        self.update_config({})
    
    def is_market_enabled(self, market: Market) -> bool:
        """检查市场是否启用"""
        market_config = self.config["markets"].get(market.value, {})
        return market_config.get("enabled", False)
    
    def is_product_enabled(self, product_type: ProductType) -> bool:
        """检查产品类型是否启用"""
        product_config = self.config["products"].get(product_type.value, {})
        return product_config.get("enabled", False)
    
    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置（兼容旧版本）"""
        # 返回第一个启用的券商配置作为默认API配置
        for broker_type, config in self.config["brokers"].items():
            if config.get("enabled", False):
                return config
        return {}
    
    def get_market_config(self, market: Market) -> Dict[str, Any]:
        """获取市场配置"""
        return self.config["markets"].get(market.value, {})
    
    def get_product_config(self, product_type: ProductType) -> Dict[str, Any]:
        """获取产品配置"""
        return self.config["products"].get(product_type.value, {})
    
    def get_screening_config(self) -> Dict[str, Any]:
        """获取筛选配置"""
        return self.config["screening"]
    
    def get_trading_config(self) -> Dict[str, Any]:
        """获取交易配置"""
        return self.config["trading"]
    
    def get_backtest_config(self) -> Dict[str, Any]:
        """获取回测配置"""
        return self.config["backtest"]
    
    def set_backtest_config(self, config: Dict[str, Any]):
        """设置回测配置"""
        self.config["backtest"] = config
        self._save_config()
    
    def get_gui_config(self) -> Dict[str, Any]:
        """获取GUI配置"""
        return self.config["gui"]
    
    def set_gui_config(self, config: Dict[str, Any]):
        """设置GUI配置"""
        self.config["gui"] = config
        self._save_config()
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True, indent=2)
            self.logger.info(f"配置已保存: {self.config_path}")
        except Exception as e:
            self.logger.error(f"配置保存失败: {e}")

    def update_config(self, updates: Dict[str, Any]):
        """更新配置"""
        def update_dict(d1, d2):
            for key, value in d2.items():
                if key in d1 and isinstance(d1[key], dict) and isinstance(value, dict):
                    update_dict(d1[key], value)
                else:
                    d1[key] = value
        
        update_dict(self.config, updates)
        
        # 保存到文件
        self._save_config()
    
    def enable_market(self, market: Market, enabled: bool = True):
        """启用或禁用市场"""
        if market.value not in self.config["markets"]:
            self.config["markets"][market.value] = {}
        
        self.config["markets"][market.value]["enabled"] = enabled
        self.update_config({})
    
    def enable_product(self, product_type: ProductType, enabled: bool = True):
        """启用或禁用产品类型"""
        if product_type.value not in self.config["products"]:
            self.config["products"][product_type.value] = {}
        
        self.config["products"][product_type.value]["enabled"] = enabled
        self.update_config({})
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置"""
        errors = []
        warnings = []
        
        # 检查券商配置
        enabled_brokers = 0
        for broker_type, config in self.config["brokers"].items():
            if config.get("enabled", False):
                enabled_brokers += 1
                # 验证券商特定配置
                broker_errors = self._validate_broker_config(broker_type, config)
                errors.extend(broker_errors)
        
        if enabled_brokers == 0:
            warnings.append("没有启用任何券商")
        
        # 检查市场与券商映射
        for market, broker_type in self.config["market_broker_mapping"].items():
            broker_config = self.config["brokers"].get(broker_type, {})
            if not broker_config.get("enabled", False):
                warnings.append(f"市场 {market} 映射的券商 {broker_type} 未启用")
        
        # 检查启用的市场
        enabled_markets = [market for market in Market if self.is_market_enabled(market)]
        if not enabled_markets:
            warnings.append("没有启用任何市场")
        
        # 检查启用的产品
        enabled_products = [product for product in ProductType if self.is_product_enabled(product)]
        if not enabled_products:
            warnings.append("没有启用任何产品类型")
        
        # 检查回测配置
        backtest_config = self.get_backtest_config()
        if backtest_config.get("initial_cash", 0) <= 0:
            errors.append("回测初始资金必须大于0")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_broker_config(self, broker_type: str, config: Dict[str, Any]) -> List[str]:
        """验证券商配置"""
        errors = []
        
        if broker_type == "longport":
            required_fields = ["app_key", "app_secret", "access_token"]
            for field in required_fields:
                if not config.get(field) or config[field].startswith("your_"):
                    errors.append(f"长桥API缺少必需字段: {field}")
        
        elif broker_type == "ibkr":
            if not config.get("host") or not config.get("port"):
                errors.append("IBKR API需要配置host和port")
        
        elif broker_type == "qmt":
            if not config.get("account_id") or config["account_id"].startswith("your_"):
                errors.append(f"{broker_type.upper()}需要配置有效的account_id")
        
        return errors


if __name__ == "__main__":
    # 测试配置管理器
    config_mgr = ConfigManager()
    print("API配置:", config_mgr.get_api_config())
    print("港股配置:", config_mgr.get_market_config(Market.HK))
    print("股票产品配置:", config_mgr.get_product_config(ProductType.STOCK))