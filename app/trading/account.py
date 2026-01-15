from abc import ABC
import json
import logging
from datetime import datetime
from pathlib import Path
from app.core import ActionType, TradeStatus
from .persistence import AccountData, TradeRecord, Position
from app.notifiers import create_notifier

logger = logging.getLogger(__name__)


class Account(ABC):
    """
    交易账户，专注于资金和持仓管理。

    职责边界：
    - 管理现金余额和持仓
    - 计算权益和收益
    - 记录交易历史
    - 不包含交易决策逻辑
    """
    ACCOUNT_DATA_FILE = Path("simulate/account.json")

    def __init__(self):
        self.notifier = create_notifier()
        self.data = AccountData()
        self.load()

    def __del__(self):
        self.save()
    def load(self):
        try:
            self.ACCOUNT_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.data = AccountData(**json.loads(self.ACCOUNT_DATA_FILE.read_text()))
            logger.info(f"账户状态已加载：{self.data}")
        except Exception as e:
            logger.error(f"加载账户数据失败：{e}")
    def save(self):
        self.ACCOUNT_DATA_FILE.write_text(json.dumps(self.data.model_dump())) 
        logger.info(f"账户状态已保存：{self.data}")
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
            action=action,
            symbol=symbol,
            quantity=quantity,
            price=price,
            cost=cost,
            commission=commission,
            reason=reason,
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
            # 更新平均成本
            self.data.position_record[trade.symbol].avg_cost = (
                current_avg_cost * current_quantity + trade.cost + trade.commission
            ) / (current_quantity + trade.quantity)
        else:
            self.data.position_record[trade.symbol] = Position(
                symbol=trade.symbol,
                quantity=trade.quantity,
                avg_cost=trade.price,
            )
        self.data.trade_record[trade.timestamp] = trade
        self.save()
        self.notifier.notify(f"交易事件：{trade}")
