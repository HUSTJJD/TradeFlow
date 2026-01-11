import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, cast
from dataclasses import dataclass

import pandas as pd

from longport.openapi import QuoteContext, Period

from app.core.config import global_config
from app.strategies import Strategy
from app.trading.position import PositionManager
from app.engines.engine import LiveEngine
from app.providers.longport import get_stock_names, get_stock_lot_sizes, fetch_candles
from app.utils.notifier import notifier

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LiveTradingConfig:
    initial_balance: float
    commission_rate: float
    position_ratio: float
    interval: int
    request_delay: float

    @classmethod
    def from_global_config(cls) -> "LiveTradingConfig":
        initial_balance = float(global_config.get("trading.initial_balance", 100000.0))
        commission_rate = float(global_config.get("trading.commission_rate", 0.0003))
        position_ratio = float(global_config.get("trading.position_ratio", 0.2))

        monitor_cfg = global_config.get("monitor", {}) or {}
        interval = int(monitor_cfg.get("interval", 60))
        request_delay = float(monitor_cfg.get("request_delay", 0.5))

        return cls(
            initial_balance=initial_balance,
            commission_rate=commission_rate,
            position_ratio=position_ratio,
            interval=interval,
            request_delay=request_delay,
        )


class LiveTradingService:
    def __init__(self, quote_ctx: QuoteContext, strategy: Strategy, config: LiveTradingConfig) -> None:
        self._quote_ctx = quote_ctx
        self._strategy = strategy
        self._config = config

    def run(self) -> Dict[str, Any]:
        from app.providers.longport import get_stock_pool

        symbols = get_stock_pool()
        if not symbols:
            logger.error("股票池为空，请先运行universe刷新")
            return {}

        from app.core.setup import get_strategy_config

        strat_config = get_strategy_config()
        period = cast(Period, strat_config["period"])
        history_count = int(strat_config["history_count"])

        stock_names = get_stock_names(self._quote_ctx, symbols)
        lot_sizes = get_stock_lot_sizes(self._quote_ctx, symbols)

        logger.info(f"实盘监控初始化完成。监控 {len(symbols)} 支股票，周期: {self._config.interval} 秒")

        position_manager = PositionManager(position_ratio=float(self._config.position_ratio))
        engine = LiveEngine(
            quote_ctx=self._quote_ctx,
            strategy=self._strategy,
            position_manager=position_manager,
            initial_capital=float(self._config.initial_balance),
            commission_rate=float(self._config.commission_rate),
            position_ratio=float(self._config.position_ratio),
        )

        engine.set_live_params(
            quote_ctx=self._quote_ctx,
            symbols=symbols,
            period=period,
            history_count=history_count,
            interval=int(self._config.interval),
            request_delay=float(self._config.request_delay),
        )

        if not engine.initialize(symbols, self._quote_ctx):
            logger.error("实盘引擎初始化失败")
            return {}

        self._load_account_state(engine)

        logger.info("开始实盘监控...")

        try:
            results = engine.run()
            self._save_account_state(engine)
            return results

        except KeyboardInterrupt:
            logger.info("程序由用户停止。")
            self._save_account_state(engine)
            return engine.get_results()
        except Exception as e:
            logger.error(f"实盘交易中发生未处理的异常: {e}")
            self._save_account_state(engine)
            return engine.get_results()

    @staticmethod
    def _load_account_state(engine: LiveEngine) -> None:
        try:
            from app.trading.persistence import AccountPersistence

            persistence = AccountPersistence("simulate/paper_account.json")

            if persistence.load(engine.account):
                logger.info("已加载之前的账户状态")
                logger.info(
                    f"当前账户状态: 现金={engine.account.cash:.2f}, "
                    f"总权益={engine.account.get_total_equity():.2f}"
                )
                if engine.account.positions:
                    logger.info(f"当前持仓: {engine.account.positions}")
            else:
                logger.info("未找到之前的账户状态，使用初始账户")

        except Exception as e:
            logger.warning(f"加载账户状态失败: {e}")

    @staticmethod
    def _save_account_state(engine: LiveEngine) -> None:
        try:
            from app.trading.persistence import AccountPersistence

            persistence = AccountPersistence("simulate/paper_account.json")
            persistence.save(engine.account)
            logger.info("账户状态已保存")
        except Exception as e:
            logger.warning(f"保存账户状态失败: {e}")


def run_live_trading(quote_ctx: QuoteContext, strategy: Strategy) -> Dict[str, Any]:
    """执行实盘交易监控（Runner entrypoint）。"""

    config = LiveTradingConfig.from_global_config()
    return LiveTradingService(quote_ctx=quote_ctx, strategy=strategy, config=config).run()
