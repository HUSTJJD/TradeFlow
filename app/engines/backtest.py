import logging
import pandas as pd
from typing import Dict, List, Any, Optional, cast
from app.core import cfg
from app.strategies import Strategy
from app.engines.engine import Engine


logger = logging.getLogger(__name__)


class BacktestEngine(Engine):
    """回测执行引擎"""

    def __init__(self):
        super().__init__()

    def run(self):
        """运行回测"""
        logger.error("回测数据为空")