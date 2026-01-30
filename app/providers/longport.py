from datetime import date

from sympy import true
from app.core import TIME_FORMAT
from .provider import Provider
import logging
from typing import Callable, Optional
from longport.openapi import QuoteContext, Config, Period, AdjustType, TradeSessions
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
        sec_static_infos = []
        for i in range(0, len(symbols), 500):
            batch = symbols[i : i + 500]
            sec_static_infos.extend(self.quote_ctx.static_info(batch))
        static_infos = []
        for quote in sec_static_infos:
            static_infos.append(
                [
                    quote.symbol,
                    quote.name_cn,
                    quote.exchange,
                    quote.currency,
                    quote.lot_size,
                    quote.total_shares,
                    quote.circulating_shares,
                    quote.hk_shares,
                    float(quote.eps),
                    float(quote.eps_ttm),
                    float(quote.bps),
                    float(quote.dividend_yield),
                    quote.stock_derivatives,
                    str(quote.board).split(".")[1],
                ]
            )
        return pd.DataFrame(
            static_infos,
            columns=[
                "symbol",
                "name_cn",
                "exchange",
                "currency",
                "lot_size",
                "total_shares",
                "circulating_shares",
                "hk_shares",
                "eps",
                "eps_ttm",
                "bps",
                "dividend_yield",
                "stock_derivatives",
                "board",
            ],
        )

    def request_history_info(
        self,
        symbol: str,
        start_date: str,
        end_date: str = date.today(),
    ) -> pd.DataFrame:
        """获取历史信息"""
        bars = self.quote_ctx.history_candlesticks_by_date(
            symbol,
            Period.Min_15,
            AdjustType.ForwardAdjust,
            start_date,
            end_date,
            TradeSessions.All,
        )
        return pd.DataFrame(bars)
