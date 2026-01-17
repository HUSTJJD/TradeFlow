import logging
import time
from datetime import datetime
from typing import Any, Dict, List, cast
from longport.openapi import Period, QuoteContext
from app.core import cfg
from app.engines.engine import Engine
from app.strategies import Strategy

logger = logging.getLogger(__name__)

PeriodLike = Period


class LiveEngine(Engine):
    """实盘执行引擎"""

    def __init__(self):
        super().__init__()

    def run(self):
        """运行实盘监控"""
        logger.info("开始实盘监控...")
        while True:
            logger.info(f"开始新的扫描周期: {datetime.now()}")
