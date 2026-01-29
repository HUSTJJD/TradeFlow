from abc import ABC, abstractmethod
import logging
from app.trading import Account
from app.providers import create_provider
from app.dataset import Dataset

logger = logging.getLogger(__name__)


class Engine(ABC):
    """策略执行引擎抽象基类，定义统一的策略执行接口。"""

    def __init__(self):
        # 初始化数据提供器
        self.provider = create_provider()
        self.dataset = Dataset(self.provider)
        self.account = Account()

    def run(self):
        """运行策略执行引擎"""
        pass
