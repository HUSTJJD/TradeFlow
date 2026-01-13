import logging
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional, cast
from longport.openapi import QuoteContext, Period
from sqlalchemy import over

from app.core import cfg
from app.strategies import Strategy
from app.engines.engine import Engine
from app.providers.longport import LongPortProvider
from app.utils.reporting import print_backtest_summary
from app.utils.plotter import create_performance_chart

logger = logging.getLogger(__name__)


class BacktestEngine(Engine):
    """回测执行引擎"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data: Dict[str, pd.DataFrame] = {}

    def run(self) -> Dict[str, Any]:
        """运行回测"""
        if not self.data:
            logger.error("回测数据为空")
            return {}
        