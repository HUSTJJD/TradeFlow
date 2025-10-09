"""筛选策略模块
支持技术面、基本面、消息面等多种筛选策略
"""

from .screening_engine import ScreeningEngine, ScreeningStrategy
from .screening_engine import (
    TechnicalScreeningStrategy, 
    FundamentalScreeningStrategy, 
    SentimentScreeningStrategy, 
    DerivativeScreeningStrategy
)

__all__ = [
    'ScreeningEngine', 'ScreeningStrategy',
    'TechnicalScreeningStrategy', 
    'FundamentalScreeningStrategy', 
    'SentimentScreeningStrategy', 
    'DerivativeScreeningStrategy'
]

module_info = {
    "name": "screening_strategies",
    "description": "筛选策略模块",
    "classes": [
        {"name": "ScreeningEngine", "description": "筛选引擎"},
        {"name": "ScreeningStrategy", "description": "筛选策略基类"},
        {"name": "TechnicalScreeningStrategy", "description": "技术面筛选策略"},
        {"name": "FundamentalScreeningStrategy", "description": "基本面筛选策略"},
        {"name": "SentimentScreeningStrategy", "description": "市场情绪筛选策略"},
        {"name": "DerivativeScreeningStrategy", "description": "衍生品筛选策略"}
    ],
    "strategy_types": [
        {"name": "technical", "description": "技术面分析"},
        {"name": "fundamental", "description": "基本面分析"},
        {"name": "sentiment", "description": "市场情绪分析"},
        {"name": "derivative", "description": "衍生品分析"}
    ]
}