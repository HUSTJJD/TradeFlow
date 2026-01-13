from datetime import datetime
import logging
from typing import Dict
from pydantic import BaseModel, ConfigDict, Field
from app.core import cfg
from app.core import ActionType, TradeStatus

logger = logging.getLogger(__name__)


class Position(BaseModel):
    """
    仓位信息。
    """

    symbol: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,32}$")
    quantity: int = Field(ge=0)
    avg_cost: float = Field(ge=0)


class TradeRecord(BaseModel):
    """
    交易记录。
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        frozen=True,
        extra="forbid",
    )
    timestamp: datetime = Field(default_factory=datetime)
    status: TradeStatus = Field()
    action: ActionType = Field()
    symbol: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,32}$")
    quantity: int = Field(ge=0)
    price: float = Field(ge=0)
    cost: float = Field(ge=0)
    commission: float = Field(ge=0)


class AccountData(BaseModel):
    """
    账户信息。
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        frozen=True,
    )
    cash: float = Field(default=cfg.account.balance)
    position_record: Dict[str, Position] = Field(default_factory=dict)
    trade_record: Dict[str, TradeRecord] = Field(default_factory=dict)
