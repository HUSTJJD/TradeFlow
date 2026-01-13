import json
import logging
from datetime import datetime
from app.core import cfg, ActionType, singleton_threadsafe, TradeStatus
from .persistence import AccountData, TradeRecord, Position
from app.notifier import create_notifier

logger = logging.getLogger(__name__)


@singleton_threadsafe
class Account:
    """
    交易账户，专注于资金和持仓管理。

    职责边界：
    - 管理现金余额和持仓
    - 计算权益和收益
    - 记录交易历史
    - 不包含交易决策逻辑
    """

    ACCOUNT_DATA_FILE = "simulate/account.json"

    def __init__(self):
        self.notifier = create_notifier()
        self.data = AccountData(**json.load(open(self.ACCOUNT_DATA_FILE)))
        logger.info(f"账户状态已加载：{self.data}")

    def __del__(self):
        json.dump(
            self.data.model_dump(),
            open(self.ACCOUNT_DATA_FILE, "w"),
            ensure_ascii=False,
            indent=2,
        )
        logger.info("账户状态已保存")

    def execute(
        self, symbol: str, price: float, action: ActionType, reason: str
    ) -> TradeStatus:
        quantity = 0
        if action == ActionType.SELL:
            quantity = self.sell(symbol, price)
        elif action == ActionType.BUY:
            quantity = self.buy(symbol, price)
        else:
            return TradeStatus.FAILED
        cost = quantity * price
        commission = cost * 0.001
        trade = TradeRecord(
            timestamp=datetime.now(),
            status=TradeStatus.SUCCESS,
            action=action,
            symbol=symbol,
            quantity=quantity,
            price=price,
            cost=cost,
            commission=commission,
        )
        self.on_trade(trade)
        return TradeStatus.SUCCESS

    def sell(self, symbol: str, price: float) -> int:
        """卖出股票 智能控仓"""
        position = self.data.position_record.get(symbol)
        if not position:
            return 0
        quantity = position.quantity
        cost = quantity * price
        if self.data.cash < cost:
            return 0
        return quantity

    def buy(self, symbol: str, price: float) -> int:
        """买入股票 智能控仓"""
        cost = price
        if self.data.cash < cost:
            return 0
        return 1

    def on_trade(self, trade: TradeRecord) -> None:
        """处理交易事件"""
        self.data.cash -= trade.cost + trade.commission
        position = self.data.position_record.get(trade.symbol)
        if position:
            current_quantity = position.quantity
            current_avg_cost = position.avg_cost
            if trade.action == ActionType.SELL:
                self.data.position_record[trade.symbol].quantity -= trade.quantity
            elif trade.action == ActionType.BUY:
                self.data.position_record[trade.symbol].quantity += trade.quantity
            self.data.position_record[trade.symbol].avg_cost = (
                current_avg_cost * current_quantity + trade.cost
            ) / (current_quantity + trade.quantity)
        else:
            self.data.position_record[trade.symbol] = Position(
                symbol=trade.symbol,
                quantity=trade.quantity,
                avg_cost=trade.price,
            )
        self.data.trade_record[trade.timestamp] = trade

        self.notifier.notify(f"交易事件：{trade}")
