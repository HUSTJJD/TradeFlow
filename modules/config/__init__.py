"""配置管理模块
负责管理多市场、多产品的配置信息
"""

from .config_manager import ConfigManager, Market, ProductType

__all__ = ['ConfigManager', 'Market', 'ProductType']

module_info = {
    "name": "config",
    "description": "配置管理模块",
    "classes": [
        {"name": "ConfigManager", "description": "配置管理器"},
        {"name": "Market", "description": "市场枚举"},
        {"name": "ProductType", "description": "产品类型枚举"}
    ]
}