from app.core import singleton_threadsafe, global_config
import logging
from .engines import create_engine

@singleton_threadsafe
class TradeFlow:
    def __init__(self) -> None:
        logging.info(f"TradeFlow 启动")

    def run(self) -> None:
        try:
            run_mode = global_config.get("run_mode", "backtest")
            logging.info(f"应用运行模式: {run_mode}")
            engine = create_engine(run_mode)
            while True:
                engine.run()
        except Exception as e:
            logging.error(f"运行出错 {e}")
