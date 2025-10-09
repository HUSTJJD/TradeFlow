"""产品类型模块
定义不同产品（股票、ETF、窝轮、牛熊证、期权）的特性和行为
"""

from .product_factory import ProductFactory, ProductBase
from .product_factory import StockProduct, ETFProduct, WarrantProduct, CBBCProduct, OptionProduct

__all__ = [
    'ProductFactory', 'ProductBase',
    'StockProduct', 'ETFProduct', 'WarrantProduct', 'CBBCProduct', 'OptionProduct',
    'ProductType'  # 添加ProductType到导出列表
]

# 从product_factory导入ProductType
from .product_factory import ProductType

module_info = {
    "name": "product_types",
    "description": "产品类型模块",
    "classes": [
        {"name": "ProductFactory", "description": "产品工厂"},
        {"name": "ProductBase", "description": "产品基类"},
        {"name": "StockProduct", "description": "股票产品"},
        {"name": "ETFProduct", "description": "ETF产品"},
        {"name": "WarrantProduct", "description": "窝轮产品"},
        {"name": "CBBCProduct", "description": "牛熊证产品"},
        {"name": "OptionProduct", "description": "期权产品"},
        {"name": "ProductType", "description": "产品类型枚举"}
    ],
    "product_types": [
        {"name": "stock", "description": "股票"},
        {"name": "etf", "description": "ETF"},
        {"name": "warrant", "description": "窝轮"},
        {"name": "cbbc", "description": "牛熊证"},
        {"name": "option", "description": "期权"}
    ]
}