"""多市场多产品交易系统模块包
模块化架构的交易系统，支持A股、港股、美股市场，以及股票、ETF、窝轮、牛熊证、期权等产品
"""

__version__ = "1.0.0"
__author__ = "Trading System Team"
__description__ = "Multi-Market Multi-Product Trading System"

# 导出主要模块
from .config.config_manager import ConfigManager, Market, ProductType
from .market_data.market_data_provider import MarketDataProvider
from .product_types.product_factory import ProductFactory, ProductBase
from .screening_strategies.screening_engine import ScreeningEngine, ScreeningStrategy
from .trading_execution.trading_engine import TradingEngine, TradingStrategy
from .utils.common_utils import DateTimeUtils, DataConverter, Logger, PerformanceMetrics

# 有条件导入main_system，避免schedule依赖问题
try:
    from .main_system import TradingSystem
    MAIN_SYSTEM_AVAILABLE = True
except ImportError as e:
    if "schedule" in str(e):
        MAIN_SYSTEM_AVAILABLE = False
        TradingSystem = None
    else:
        raise

# 导出所有主要类
__all__ = [
    # 配置管理
    'ConfigManager', 'Market', 'ProductType',
    
    # 市场数据
    'MarketDataProvider',
    
    # 产品类型
    'ProductFactory', 'ProductBase',
    
    # 筛选策略
    'ScreeningEngine', 'ScreeningStrategy',
    
    # 交易执行
    'TradingEngine', 'TradingStrategy',
    
    # 工具函数
    'DateTimeUtils', 'DataConverter', 'Logger', 'PerformanceMetrics',
]

# 如果有条件地添加TradingSystem
if MAIN_SYSTEM_AVAILABLE:
    __all__.append('TradingSystem')

# 包信息
package_info = {
    "name": "trading_system_modules",
    "version": __version__,
    "description": __description__,
    "author": __author__,
    "modules": {
        "config": "配置管理模块",
        "market_data": "市场数据模块", 
        "product_types": "产品类型模块",
        "screening_strategies": "筛选策略模块",
        "trading_execution": "交易执行模块",
        "utils": "工具函数模块",
        "main_system": "主系统集成模块"
    },
    "main_system_available": MAIN_SYSTEM_AVAILABLE
}

def get_package_info():
    """获取包信息"""
    return package_info.copy()

def list_available_modules():
    """列出可用模块"""
    return list(package_info["modules"].keys())

def get_module_description(module_name):
    """获取模块描述"""
    return package_info["modules"].get(module_name, "未知模块")

# 版本兼容性检查
def check_compatibility():
    """检查系统兼容性"""
    import sys
    python_version = sys.version_info
    
    if python_version < (3, 8):
        raise RuntimeError(f"需要Python 3.8+，当前版本: {python_version.major}.{python_version.minor}")
    
    return {
        "python_version": f"{python_version.major}.{python_version.minor}.{python_version.micro}",
        "compatible": python_version >= (3, 8),
        "requirements": "Python 3.8+, longport, pandas, numpy, requests"
    }

# 初始化时检查兼容性
try:
    compatibility_info = check_compatibility()
    if not compatibility_info["compatible"]:
        print(f"警告: Python版本不兼容，建议升级到3.8+")
except Exception as e:
    print(f"兼容性检查失败: {e}")