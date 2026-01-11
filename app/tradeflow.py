import logging
from typing import Optional
from longport.openapi import Config as LpConfig, QuoteContext
from app.core.config import global_config
from app.strategies import create_strategy
from app.engines import create_engine
from app.trading.account import PaperAccount

class TradeFlow:
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        app_key = global_config.get("longport.app_key")
        app_secret = global_config.get("longport.app_secret")
        access_token = global_config.get("longport.access_token")
        if not all([app_key, app_secret, access_token]):
            self._logger.error("缺少 LongPort 配置。请检查 config.yaml 或环境变量。")
            raise ValueError("Missing LongPort configuration.")
        config = LpConfig(app_key=app_key, app_secret=app_secret, access_token=access_token)

        self._quote_ctx = QuoteContext(config)
        strategy_name = global_config.get("strategy.name", "MACD")
        strategy_params = global_config.get("strategy.params", {})
        self._strategy = create_strategy(strategy_name, **strategy_params)

    def run(self) -> None:
        run_mode = global_config.get("run_mode", "backtest")
        self._logger.info(f"应用运行模式: {run_mode}")
        engine = create_engine(run_mode, self._quote_ctx, self._strategy)
        while True:
            engine.run()