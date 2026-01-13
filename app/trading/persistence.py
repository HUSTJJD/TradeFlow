from datetime import datetime
import json
import logging
from re import A
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field
from yarg import get
from app.core import cfg

logger = logging.getLogger(__name__)


class Position(BaseModel):
    """
    仓位信息。
    """

    symbol: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,32}$")
    quantity: int = Field(ge=0)
    avg_cost: float = Field(ge=0)
    latest_price: float = Field(ge=0)


class TradeRecord(BaseModel):
    """
    交易记录。
    """

    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,32}$")
    timestamp: datetime = Field(default_factory=datetime)
    symbol: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,32}$")
    action: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,32}$")
    quantity: int = Field(ge=0)
    price: float = Field(ge=0)
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
    positions: List[Position] = Field(default_factory=list)
    trade_record: List[TradeRecord] = Field(default_factory=list)


ACCOUNT_DATA_FILE = "simulate/account.json"


def load_account_data() -> AccountData:
    """
    获取账户信息。
    """
    with open(ACCOUNT_DATA_FILE, "r") as f:
        data = f.read()
        return AccountData(**json.loads(data))
    return AccountData()


def save_account_data(data: AccountData) -> None:
    with open(ACCOUNT_DATA_FILE, "w") as f:
        f.write(data.model_dump_json())
    logger.info("账户状态已保存")
