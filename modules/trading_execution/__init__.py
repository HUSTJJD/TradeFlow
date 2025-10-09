"""交易执行模块
支持不同产品的交易逻辑和风险管理
"""

from .trading_engine import TradingEngine, TradingStrategy, RiskManager
from .trading_engine import MomentumTradingStrategy, MeanReversionStrategy

__all__ = [
    'TradingEngine', 'TradingStrategy', 'RiskManager',
    'MomentumTradingStrategy', 'MeanReversionStrategy'
]

module_info = {
    "name": "trading_execution",
    "description": "交易执行模块",
    "classes": [
        {"name": "TradingEngine", "description": "交易引擎"},
        {"name": "TradingStrategy", "description": "交易策略基类"},
        {"name": "RiskManager", "description": "风险管理器"},
        {"name": "MomentumTradingStrategy", "description": "动量交易策略"},
        {"name": "MeanReversionStrategy", "description": "均值回归策略"}
    ],
    "strategy_types": [
        {"name": "momentum", "description": "动量策略"},
        {"name": "mean_reversion", "description": "均值回归策略"}
    ],
    "functions": [
        {"name": "execute_trade", "description": "执行交易"},
        {"name": "get_account_balance", "description": "获取账户余额"},
        {"name": "get_positions", "description": "获取持仓信息"}
    ]
}