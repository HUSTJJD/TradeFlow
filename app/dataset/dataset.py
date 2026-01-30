import os
from pathlib import Path
import logging
from datetime import datetime, timedelta, date
import random
import time
import pandas as pd
from app.core import TIME_FORMAT
from app.providers import Provider

logger = logging.getLogger(__name__)


class Dataset:
    """数据集工具类，提供市场标的和历史数据的获取与更新功能。"""

    SYMBOL_FILE_PATH = Path("data/watchlist_symbols.csv")
    STATIC_INFO_FILE_PATH = Path("data/static_infos.csv")
    DATA_FILE_PATH = Path("data/stocks/")

    def __init__(self, provider: Provider) -> None:
        self.SYMBOL_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.STATIC_INFO_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.DATA_FILE_PATH.mkdir(parents=True, exist_ok=True)
        self.provider = provider
        self.update_static_infos()
        self.update_dynamic_infos(self.static_infos.index.tolist())
        self.stock_datas = pd.DataFrame()

    def update_dynamic_infos(self, symbols: list) -> None:
        for symbol in symbols:
            # 增量更新
            file_path = self.DATA_FILE_PATH.joinpath(f"{symbol}.parquet")
            stock = self.static_infos.loc[symbol]
            if stock is None or stock.empty:
                continue
            start_date = stock.get("start_date") or (
                date.today() - timedelta(days=1)
            )
            end_date = stock.get("end_date") or date.today()
            if os.path.exists(file_path):
                df = pd.read_parquet(file_path)
            else:
                df = pd.DataFrame()
            try:
                new_df = self.provider.request_history_info(
                    symbol, start_date, end_date
                )
                df = pd.concat([df, new_df], ignore_index=True)
                logger.info(f"{symbol} 历史数据已更新，数据量: {len(df)} 条")
                df.to_parquet(file_path)
                stock["end_date"] = end_date
                if pd.notna(stock["start_date"]):
                    stock["start_date"] = min(stock["start_date"], start_date)
                self.static_infos.loc[symbol] = stock
            except Exception as e:
                logger.error(f"更新 {symbol} 历史数据失败: {e}")
            time.sleep(random.uniform(1, 2))

    def update_static_infos(self):
        if os.path.exists(self.STATIC_INFO_FILE_PATH):
            file_mtime = datetime.fromtimestamp(
                os.path.getmtime(self.STATIC_INFO_FILE_PATH)
            )
            if datetime.now() - file_mtime < timedelta(days=30):
                self.static_infos = pd.read_csv(
                    self.STATIC_INFO_FILE_PATH, index_col="symbol"
                )
        else:
            if not os.path.exists(self.SYMBOL_FILE_PATH):
                all_symbols = ["700.Hk"]
            else:
                all_symbols = pd.read_csv(self.SYMBOL_FILE_PATH)["symbol"].tolist()
            static_info = self.provider.request_static_info(all_symbols)
            static_info.to_csv(self.STATIC_INFO_FILE_PATH, index=False)
            self.static_infos = static_info
