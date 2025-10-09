"""工具函数模块
包含日期处理、数据转换、日志记录等通用功能
"""

from .common_utils import (
    DateTimeUtils, 
    DataConverter, 
    Logger, 
    PerformanceMetrics, 
    ConfigLoader
)

__all__ = [
    'DateTimeUtils', 
    'DataConverter', 
    'Logger', 
    'PerformanceMetrics', 
    'ConfigLoader'
]

module_info = {
    "name": "utils",
    "description": "工具函数模块",
    "classes": [
        {"name": "DateTimeUtils", "description": "日期时间工具类"},
        {"name": "DataConverter", "description": "数据转换工具类"},
        {"name": "Logger", "description": "日志记录工具类"},
        {"name": "PerformanceMetrics", "description": "性能指标计算工具类"},
        {"name": "ConfigLoader", "description": "配置加载工具类"}
    ],
    "functions": [
        {"name": "is_trading_time", "description": "判断是否为交易时间"},
        {"name": "decimal_to_float", "description": "Decimal转float"},
        {"name": "calculate_sharpe_ratio", "description": "计算夏普比率"},
        {"name": "load_yaml_config", "description": "加载YAML配置"}
    ]
}