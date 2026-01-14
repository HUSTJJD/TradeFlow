from app.core import cfg
import logging
from .engines import create_engine

class TradeFlow:
    def __init__(self) -> None:
        logging.info(f"TradeFlow 启动")

    def run(self) -> None:
        try:
            trade_mode = cfg.app.trade_mode
            logging.info(f"应用运行模式: {trade_mode}")
            engine = create_engine(trade_mode)
            engine.run()
        except Exception as e:
            logging.error(f"运行出错 {e}")
