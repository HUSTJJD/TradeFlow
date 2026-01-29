import logging
from app.engines.engine import Engine


logger = logging.getLogger(__name__)


class BacktestEngine(Engine):
    """回测执行引擎"""

    def __init__(self):
        super().__init__()

    def run(self):
        """运行回测"""
        super().run()