"""市场数据模块
负责获取不同市场、不同产品的实时数据
"""

from .market_data_provider import MarketDataProvider

__all__ = ['MarketDataProvider']

module_info = {
    "name": "market_data",
    "description": "市场数据模块",
    "classes": [
        {"name": "MarketDataProvider", "description": "市场数据提供器"}
    ],
    "functions": [
        {"name": "get_real_time_quotes", "description": "获取实时报价"},
        {"name": "get_candlestick_data", "description": "获取K线数据"},
        {"name": "get_market_symbols", "description": "获取市场标的列表"}
    ]
}