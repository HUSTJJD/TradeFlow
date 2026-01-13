from .provider import Provider
import logging
from typing import Callable, Optional
from longport.openapi import QuoteContext


logger = logging.getLogger(__name__)


class LongPortProvider(Provider):
    """长桥API数据提供器"""

    def __init__(self):
        super().__init__()
        self.quote_ctx: Optional[QuoteContext] = None

    def request_buy(
        self, symbol: str, quantity: int, callback: Optional[Callable]
    ) -> None:
        pass

    def request_sell(
        self, symbol: str, quantity: int, callback: Optional[Callable]
    ) -> None:
        pass
