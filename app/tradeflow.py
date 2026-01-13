from app.core import TradeMode, singleton_threadsafe, cfg
import logging
from .engines import create_engine
@singleton_threadsafe
class TradeFlow:
    def __init__(self) -> None:
        logging.info(f"TradeFlow 启动")

    def run(self) -> None:
        try:
            run_mode_raw = cfg.app.run_mode
            logging.info(f"应用运行模式: {run_mode_raw}")

            run_mode = (
                run_mode_raw
                if isinstance(run_mode_raw, TradeMode)
                else TradeMode(str(run_mode_raw).upper())
            )
            engine = create_engine(run_mode)
            while True:
                engine.run()
        except Exception as e:
            logging.error(f"运行出错 {e}")
