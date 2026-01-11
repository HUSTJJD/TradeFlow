import logging
import json
from math import floor
import os
from typing import Dict, Any, Optional, List
from app.core.constants import SignalType

logger = logging.getLogger(__name__)


class PaperAccount:
    """
    模拟交易账户，用于实时模拟盘。
    """

    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.0003,
        on_trade: Optional[Any] = None,
    ):
        self.commission_rate = commission_rate
        self.on_trade = on_trade

        self.cash = initial_capital
        self.initial_capital = initial_capital
        self.positions: Dict[str, int] = {}  # symbol -> quantity
        self.avg_costs: Dict[str, float] = {}  # symbol -> avg_cost
        self.latest_prices: Dict[str, float] = {}  # symbol -> last known price
        self.trades: List[Dict[str, Any]] = []  # 交易记录
        self.stock_names: Dict[str, str] = {}   # symbol -> name
        self.processed_signals: set = set() # 已处理的信号ID集合
        self.equity_history: List[Dict[str, Any]] = [] # 权益历史 [{"time": "2023-01-01", "equity": 100000}]

    def set_stock_names(self, names: Dict[str, str]):
        """设置股票名称映射"""
        self.stock_names = names

    def record_equity(self, time: Any, equity: float):
        """
        记录当前权益。
        策略：每天只保留最后一条记录。
        """
        time_str = str(time).split(" ")[0] # 只取日期部分 YYYY-MM-DD

        if not self.equity_history:
            self.equity_history.append({"time": time_str, "equity": equity})
            return

        last_record = self.equity_history[-1]
        last_date = str(last_record["time"]).split(" ")[0]

        if time_str == last_date:
            last_record["equity"] = equity
            last_record["time"] = time_str
        else:
            self.equity_history.append({"time": time_str, "equity": equity})

    def get_trade_stats(self) -> Dict[str, Any]:
        """计算交易统计信息，包括胜率等。

        统计口径：以“平仓”为一次交易（卖出后 `position_after==0`）。
        """
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        total_pnl_ratio = 0.0

        for trade in self.trades:
            if trade["action"] != SignalType.SELL:
                continue

            if trade.get("position_after", 0) != 0:
                continue

            total_trades += 1
            profit_ratio = trade.get("profit_ratio", 0.0)
            total_pnl_ratio += profit_ratio

            if profit_ratio > 0:
                winning_trades += 1
            else:
                losing_trades += 1

        win_rate = (winning_trades / total_trades) if total_trades > 0 else 0.0
        avg_pnl_ratio = (total_pnl_ratio / total_trades) if total_trades > 0 else 0.0

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "avg_pnl_ratio": avg_pnl_ratio,
        }

    def update_price(self, symbol: str, price: float):
        """更新股票最新价格"""
        self.latest_prices[symbol] = price

    def get_total_equity(self) -> float:
        """计算当前总权益（现金 + 持仓市值）"""
        equity = self.cash
        for symbol, quantity in self.positions.items():
            if quantity > 0:
                price = self.latest_prices.get(symbol, self.avg_costs.get(symbol, 0.0))
                equity += quantity * price
        return equity

    def buy(
        self,
        symbol: str,
        price: float,
        quantity: int,
        time: Any,
        reason: str,
        signal_id: Optional[str] = None,
        factors: Optional[Dict[str, Any]] = None,
        trade_tag: Optional[str] = None,
    ) -> bool:
        """执行模拟买入"""
        if signal_id and signal_id in self.processed_signals:
            logger.info(f"[{time}] 信号 {signal_id} 已处理，跳过买入操作")
            return False

        if self.cash <= 0:
            return False

        self.update_price(symbol, price)

        cost = quantity * price
        commission = cost * self.commission_rate

        if self.cash < cost + commission:
            logger.warning(
                f"[{time}] 资金不足: 需要 {cost + commission:.2f}, 可用 {self.cash:.2f}"
            )
            return False

        current_pos = self.positions.get(symbol, 0)
        current_avg_cost = self.avg_costs.get(symbol, 0.0)

        if current_pos + quantity > 0:
            new_avg_cost = (current_pos * current_avg_cost + cost) / (
                current_pos + quantity
            )
            self.avg_costs[symbol] = new_avg_cost

        self.cash -= round(cost + commission, 2)
        self.positions[symbol] = current_pos + quantity

        if signal_id:
            self.processed_signals.add(signal_id)

        self.trades.append(
            {
                "time": str(time),
                "action": SignalType.BUY,
                "symbol": symbol,
                "price": price,
                "quantity": quantity,
                "commission": commission,
                "reason": reason,
                "signal_id": signal_id,
                "factors": factors,
                "trade_tag": trade_tag,
                "position_before": current_pos,
                "position_after": self.positions[symbol],
            }
        )

        if self.on_trade:
            try:
                self.on_trade(self)
            except Exception as e:
                logger.error(f"执行交易回调失败: {e}")

        total_asset = self.get_total_equity()
        trade_ratio = cost / total_asset if total_asset > 0 else 0.0
        position_ratio = (
            (self.positions[symbol] * price) / total_asset if total_asset > 0 else 0.0
        )

        logger.info(
            f"[{time}] 买入: 股票 {self.stock_names.get(symbol, symbol):<6}, 数量 {quantity:>6d}({trade_ratio:>6.1%}), 价格 {price:>8.2f}, 费用 {commission:>7.2f}, "
            f"盈亏比 {'0.00%':>7}, 仓位 {position_ratio:>6.1%}, 原因 {reason}"
        )
        return True

    def sell(
        self,
        symbol: str,
        price: float,
        quantity: int,
        time: Any,
        reason: str,
        signal_id: Optional[str] = None,
        factors: Optional[Dict[str, Any]] = None,
        trade_tag: Optional[str] = None,
    ) -> bool:
        """执行模拟卖出（quantity 可小于当前持仓，从而实现减仓/做T）"""
        if signal_id and signal_id in self.processed_signals:
            logger.info(f"[{time}] 信号 {signal_id} 已处理，跳过卖出操作")
            return False

        self.update_price(symbol, price)

        current_pos = self.positions.get(symbol, 0)
        if current_pos <= 0:
            return False

        quantity = min(quantity, current_pos)
        if quantity <= 0:
            return False

        avg_cost = self.avg_costs.get(symbol, 0.0)
        revenue = quantity * price
        commission = revenue * self.commission_rate

        profit_ratio = (price - avg_cost) / avg_cost if avg_cost > 0 else 0.0

        self.cash += round(revenue - commission, 2)
        self.positions[symbol] = current_pos - quantity
        if self.positions[symbol] == 0:
            self.avg_costs[symbol] = 0.0

        if signal_id:
            self.processed_signals.add(signal_id)

        self.trades.append(
            {
                "time": str(time),
                "action": SignalType.SELL,
                "symbol": symbol,
                "price": price,
                "quantity": quantity,
                "commission": commission,
                "reason": reason,
                "profit_ratio": profit_ratio,
                "signal_id": signal_id,
                "factors": factors,
                "trade_tag": trade_tag,
                "position_before": current_pos,
                "position_after": self.positions[symbol],
            }
        )

        if self.on_trade:
            try:
                self.on_trade(self)
            except Exception as e:
                logger.error(f"执行交易回调失败: {e}")

        total_asset = self.get_total_equity()
        trade_ratio = revenue / total_asset if total_asset > 0 else 0.0

        position_ratio = (
            (self.positions[symbol] * price) / total_asset if total_asset > 0 else 0.0
        )

        logger.info(
            f"[{time}] 卖出: 股票 {self.stock_names.get(symbol, symbol):<6}, 数量 {quantity:>6d}({trade_ratio:>6.1%}), 价格 {price:>8.2f}, 费用 {commission:>7.2f}, "
            f"盈亏比 {profit_ratio:>7.2%}, 仓位 {position_ratio:>6.1%}, 原因 {reason}"
        )
        return True
