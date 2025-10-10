"""通用工具模块
包含日期处理、数据转换、日志记录等通用功能
"""

import json
import yaml
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal


class DateTimeUtils:
    """日期时间工具类"""
    
    @staticmethod
    def is_trading_time(market: str, current_time: datetime = None) -> bool:
        """判断是否为交易时间"""
        if current_time is None:
            current_time = datetime.now()
        
        # 市场交易时间配置
        trading_hours = {
            "HK": {"start": "09:30", "end": "16:00"},  # 港股
            "US": {"start": "21:30", "end": "04:00"},  # 美股（次日）
            "CN": {"start": "09:30", "end": "15:00"}   # A股
        }
        
        if market not in trading_hours:
            return False
        
        config = trading_hours[market]
        start_time = datetime.strptime(config["start"], "%H:%M").time()
        end_time = datetime.strptime(config["end"], "%H:%M").time()
        current_time_only = current_time.time()
        
        # 处理美股跨日情况
        if market == "US":
            if current_time_only >= datetime.strptime("00:00", "%H:%M").time():
                return current_time_only <= end_time
            else:
                return current_time_only >= start_time
        else:
            return start_time <= current_time_only <= end_time
    
    @staticmethod
    def is_weekend(date: datetime = None) -> bool:
        """判断是否为周末"""
        if date is None:
            date = datetime.now()
        return date.weekday() >= 5
    
    @staticmethod
    def get_next_trading_day(market: str, current_date: datetime = None) -> datetime:
        """获取下一个交易日"""
        if current_date is None:
            current_date = datetime.now()
        
        next_day = current_date + timedelta(days=1)
        
        # 跳过周末
        while DateTimeUtils.is_weekend(next_day):
            next_day += timedelta(days=1)
        
        return next_day
    
    @staticmethod
    def format_timestamp(timestamp: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化时间戳"""
        return timestamp.strftime(format_str)
    
    @staticmethod
    def parse_timestamp(timestamp_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
        """解析时间戳字符串"""
        return datetime.strptime(timestamp_str, format_str)


class DataConverter:
    """数据转换工具类"""
    
    @staticmethod
    def decimal_to_float(data: Any) -> Any:
        """将Decimal类型转换为float"""
        if isinstance(data, Decimal):
            return float(data)
        elif isinstance(data, dict):
            return {k: DataConverter.decimal_to_float(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [DataConverter.decimal_to_float(item) for item in data]
        else:
            return data
    
    @staticmethod
    def normalize_data(data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """数据标准化"""
        normalized = {}
        
        for field, config in schema.items():
            value = data.get(field)
            if value is None:
                if 'default' in config:
                    normalized[field] = config['default']
                else:
                    continue
            
            # 类型转换
            if 'type' in config:
                try:
                    if config['type'] == 'float':
                        normalized[field] = float(value)
                    elif config['type'] == 'int':
                        normalized[field] = int(value)
                    elif config['type'] == 'str':
                        normalized[field] = str(value)
                    elif config['type'] == 'bool':
                        normalized[field] = bool(value)
                    else:
                        normalized[field] = value
                except (ValueError, TypeError):
                    normalized[field] = config.get('default', value)
            else:
                normalized[field] = value
        
        return normalized
    
    @staticmethod
    def calculate_percentage_change(current: float, previous: float) -> float:
        """计算百分比变化"""
        if previous == 0:
            return 0.0
        return (current - previous) / previous * 100
    
    @staticmethod
    def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
        """安全除法"""
        if denominator == 0:
            return default
        return numerator / denominator


class Logger:
    """日志记录工具类"""
    
    _instance = None
    
    def __new__(cls, name: str = "trading_system", level: int = logging.INFO):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup_logger(name, level)
        return cls._instance
    
    def _setup_logger(self, name: str, level: int):
        """设置日志记录器"""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            
            # 文件处理器
            file_handler = logging.FileHandler(f"{name}.log", encoding='utf-8')
            file_handler.setLevel(level)
            
            # 格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str):
        """记录信息日志"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """记录警告日志"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """记录错误日志"""
        self.logger.error(message)
    
    def debug(self, message: str):
        """记录调试日志"""
        self.logger.debug(message)


class PerformanceMetrics:
    """性能指标计算工具类"""
    
    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
        """计算夏普比率"""
        if not returns:
            return 0.0
        
        avg_return = sum(returns) / len(returns)
        std_dev = pd.Series(returns).std()
        
        if std_dev == 0:
            return 0.0
        
        return (avg_return - risk_free_rate) / std_dev
    
    @staticmethod
    def calculate_max_drawdown(prices: List[float]) -> float:
        """计算最大回撤"""
        if not prices:
            return 0.0
        
        peak = prices[0]
        max_drawdown = 0.0
        
        for price in prices:
            if price > peak:
                peak = price
            drawdown = (peak - price) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown * 100  # 转换为百分比
    
    @staticmethod
    def calculate_volatility(returns: List[float]) -> float:
        """计算波动率"""
        if len(returns) < 2:
            return 0.0
        
        return pd.Series(returns).std() * 100  # 年化波动率
    
    @staticmethod
    def calculate_win_rate(trades: List[Dict[str, Any]]) -> float:
        """计算胜率"""
        if not trades:
            return 0.0
        
        winning_trades = [trade for trade in trades if trade.get('profit_loss', 0) > 0]
        return len(winning_trades) / len(trades) * 100


class ConfigLoader:
    """配置加载工具类
    注意：这是一个简单的配置加载工具类，主要用于快速加载配置文件。
    对于完整的配置管理功能，请使用 modules.config.config_manager.ConfigManager 类。
    """
    
    @staticmethod
    def load_yaml_config(file_path: str) -> Dict[str, Any]:
        """加载YAML配置文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"配置文件不存在: {file_path}")
            return {}
        except yaml.YAMLError as e:
            print(f"YAML解析错误: {e}")
            return {}
    
    @staticmethod
    def save_yaml_config(file_path: str, config: Dict[str, Any]):
        """保存配置到YAML文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                yaml.dump(config, file, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    @staticmethod
    def load_json_config(file_path: str) -> Dict[str, Any]:
        """加载JSON配置文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"配置文件不存在: {file_path}")
            return {}
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return {}


if __name__ == "__main__":
    # 测试工具类
    print("=== 日期时间工具测试 ===")
    print(f"当前是否为港股交易时间: {DateTimeUtils.is_trading_time('HK')}")
    print(f"当前是否为周末: {DateTimeUtils.is_weekend()}")
    
    print("\n=== 数据转换工具测试 ===")
    test_data = {"price": Decimal("100.5"), "volume": 1000}
    converted = DataConverter.decimal_to_float(test_data)
    print(f"Decimal转换: {converted}")
    
    print("\n=== 性能指标测试 ===")
    returns = [0.01, -0.02, 0.03, -0.01, 0.02]
    sharpe = PerformanceMetrics.calculate_sharpe_ratio(returns)
    print(f"夏普比率: {sharpe:.4f}")