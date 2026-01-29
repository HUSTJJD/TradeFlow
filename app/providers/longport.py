from .provider import Provider
import logging
from typing import Callable, Optional
from longport.openapi import QuoteContext, Config
import pandas as pd
import os
from app.core import cfg

logger = logging.getLogger(__name__)


class LongPortProvider(Provider):
    """长桥API数据提供器"""

    def __init__(self):
        super().__init__()
        os.environ["LONGPORT_REGION"] = "cn"
        config = Config(
            app_key=cfg.longport.app_key,
            app_secret=cfg.longport.app_secret,
            access_token=cfg.longport.access_token,
        )
        self.quote_ctx: Optional[QuoteContext] = QuoteContext(config)

    def request_buy(
        self, symbol: str, quantity: int, callback: Optional[Callable]
    ) -> None:
        pass

    def request_sell(
        self, symbol: str, quantity: int, callback: Optional[Callable]
    ) -> None:
        pass

    def convert_a_symbol(self, symbol: str) -> str:
        code = symbol
        # 沪市主板 (600, 601, 603, 605)
        if code.startswith("60"):
            return f"{code}.SH"
        # 沪市科创板 (688, 689)
        elif code.startswith("68"):
            return f"{code}.SH"
        # 沪市B股 (900)
        elif code.startswith("900"):
            return f"{code}.SH"
        # 深市主板 (000, 001, 002, 003)
        elif code.startswith("00"):
            return f"{code}.SZ"
        # 深市创业板 (300, 301)
        elif code.startswith("30"):
            return f"{code}.SZ"
        # 深市B股 (200)
        elif code.startswith("200"):
            return f"{code}.SZ"
        # 北交所 (43, 83, 87, 92)
        elif (
            code.startswith("83")
            or code.startswith("87")
            or code.startswith("43")
            or code.startswith("92")
        ):
            return f"{code}.BJ"
        # 新三板 (400, 420)
        elif code.startswith("400") or code.startswith("420"):
            return f"{code}.NQ"

        return f"{code}.UNKNOWN"

    def convert_hk_symbol(self, symbol: str) -> str:
        return f"{symbol}.HK"

    def request_static_info(self, symbols: list[str]) -> pd.DataFrame:
        df = pd.DataFrame()
        for i in range(0, len(symbols), 500):
            batch = symbols[i : i + 500]
            df = pd.concat([df, self.quote_ctx.static_info(batch)])
        return df
