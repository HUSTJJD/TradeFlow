import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Union, Optional
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class Strategy(ABC):
    """
    所有交易策略的抽象基类。
    提供统一的策略接口和生命周期管理。
    """

    def __init__(self, name: Optional[str] = None, description: str = "") -> None:
        """
        初始化策略。
        
        Args:
            name: 策略名称，如果为None则使用类名
            description: 策略描述
        """
        self.name = name or self.__class__.__name__
        self.description = description
        self._initialized = False
        self._last_analysis_time: Optional[datetime] = None
        self._analysis_count = 0
    
    def initialize(self, **kwargs: Any) -> bool:
        """
        初始化策略，在第一次分析前调用。
        
        Args:
            **kwargs: 初始化参数
            
        Returns:
            bool: 初始化是否成功
        """
        if self._initialized:
            logger.warning(f"Strategy {self.name} already initialized")
            return True
        
        try:
            result = self._on_initialize(**kwargs)
            self._initialized = True
            logger.info(f"Strategy {self.name} initialized successfully")
            return result
        except Exception as e:
            logger.error(f"Failed to initialize strategy {self.name}: {e}")
            return False
    
    def _on_initialize(self, **kwargs: Any) -> bool:
        """
        子类可以重写的初始化钩子方法。
        
        Args:
            **kwargs: 初始化参数
            
        Returns:
            bool: 初始化是否成功
        """
        return True
    
    @abstractmethod
    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        分析市场数据并生成交易信号。

        Args:
            symbol: 股票代码（例如 '700.HK'）。
            df: 包含至少 'close' 列的 K 线数据 DataFrame。

        Returns:
            包含信号的字典:
            {
                'action': 'BUY' | 'SELL' | 'HOLD',
                'price': float,
                'reason': str,
                'factors': Dict[str, Any]  # 可选：策略因子值
            }
        """
        pass
    
    def analyze_with_initialization(self, symbol: str, df: pd.DataFrame, 
                                  **init_kwargs: Any) -> Dict[str, Any]:
        """
        带初始化的分析方法，确保策略在使用前已初始化。
        
        Args:
            symbol: 股票代码
            df: K线数据DataFrame
            **init_kwargs: 初始化参数
            
        Returns:
            交易信号字典
        """
        if not self._initialized:
            if not self.initialize(**init_kwargs):
                return {
                    "action": "HOLD", 
                    "reason": "策略初始化失败",
                    "price": float(df["close"].iloc[-1]) if len(df) > 0 else 0.0
                }
        
        return self.analyze(symbol, df)
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取策略信息。
        
        Returns:
            策略信息字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "class_name": self.__class__.__name__,
            "initialized": self._initialized,
            "analysis_count": self._analysis_count,
            "last_analysis_time": self._last_analysis_time
        }
    
    def validate_data(self, df: pd.DataFrame, required_columns: Optional[list[str]] = None) -> bool:
        """
        验证输入数据的有效性。
        
        Args:
            df: 待验证的DataFrame
            required_columns: 必需的数据列，默认为['close']
            
        Returns:
            bool: 数据是否有效
        """
        if required_columns is None:
            required_columns = ["close"]

        if df.empty:
            logger.warning("Empty DataFrame provided")
            return False
        
        for col in required_columns:
            if col not in df.columns:
                logger.warning(f"Required column '{col}' not found in DataFrame")
                return False
        
        return True
    
    def cleanup(self) -> None:
        """
        清理策略资源，在策略不再使用时调用。
        """
        try:
            self._on_cleanup()
            self._initialized = False
            logger.info(f"Strategy {self.name} cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during strategy cleanup {self.name}: {e}")
    
    def _on_cleanup(self) -> None:
        """
        子类可以重写的清理钩子方法。
        """
        pass
    
    def __str__(self) -> str:
        """返回策略的字符串表示"""
        return f"{self.__class__.__name__}(name='{self.name}')"
    
    def __repr__(self) -> str:
        """返回策略的详细表示"""
        return f"{self.__class__.__name__}(name='{self.name}', description='{self.description}')"
