from abc import ABC
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from app.core.constants import SignalType

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

    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.0003,
        on_trade: Optional[Callable] = None,
    ):
        self.commission_rate = commission_rate
        self.on_trade = on_trade

        self.cash = initial_capital
        self.initial_capital = initial_capital
        self.positions: Dict[str, int] = {}  # symbol -> quantity
        self.avg_costs: Dict[str, float] = {}  # symbol -> avg_cost
        self.latest_prices: Dict[str, float] = {}  # symbol -> last known price
        self.trades: List[Dict[str, Any]] = []  # 交易记录
        self.stock_names: Dict[str, str] = {}  # symbol -> name
        self.equity_history: List[Dict[str, Any]] = (
            []
        )  # 权益历史 [{"time": "2023-01-01", "equity": 100000}]

        # 信号处理状态（由TradeManager管理）
        self._processed_signals: set = set()

    def set_stock_names(self, names: Dict[str, str]) -> None:
        """设置股票名称映射"""
        self.stock_names = names

    def update_price(self, symbol: str, price: float) -> None:
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

    def get_position_value(self, symbol: str) -> float:
        """获取指定股票的持仓市值"""
        quantity = self.positions.get(symbol, 0)
        if quantity <= 0:
            return 0.0
        price = self.latest_prices.get(symbol, self.avg_costs.get(symbol, 0.0))
        return quantity * price

    def get_position_ratio(self, symbol: str) -> float:
        """获取指定股票的仓位比例"""
        total_equity = self.get_total_equity()
        if total_equity <= 0:
            return 0.0
        return self.get_position_value(symbol) / total_equity

    def record_equity(
        self, timestamp: datetime, equity: Optional[float] = None
    ) -> None:
        """
        记录当前权益。
        策略：每天只保留最后一条记录。
        """
        if equity is None:
            equity = self.get_total_equity()

        time_str = str(timestamp).split(" ")[0]  # 只取日期部分 YYYY-MM-DD

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
        """
        计算交易统计信息，包括胜率等。

        统计口径：以"平仓"为一次交易（卖出后 `position_after==0`）。
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

    def buy(
        self,
        symbol: str,
        price: float,
        quantity: int,
        time: datetime,
        reason: str,
        signal_id: Optional[str] = None,
        factors: Optional[Dict[str, Any]] = None,
        trade_tag: Optional[str] = None,
    ) -> bool:
        """
        执行买入操作（纯资金和持仓管理）。

        Args:
            symbol: 股票代码
            price: 买入价格
            quantity: 买入数量
            time: 交易时间
            reason: 买入原因
            signal_id: 信号ID（可选）
            factors: 策略因子（可选）
            trade_tag: 交易标签（可选）

        Returns:
            是否成功买入
        """
        if quantity <= 0:
            logger.warning(f"买入数量必须大于0: {quantity}")
            return False

        if self.cash <= 0:
            logger.warning(f"资金不足: {self.cash:.2f}")
            return False

        # 计算成本和佣金
        cost = quantity * price
        commission = cost * self.commission_rate
        total_cost = cost + commission

        if self.cash < total_cost:
            logger.warning(f"资金不足: 需要 {total_cost:.2f}, 可用 {self.cash:.2f}")
            return False

        # 更新持仓和成本
        current_pos = self.positions.get(symbol, 0)
        current_avg_cost = self.avg_costs.get(symbol, 0.0)

        if current_pos + quantity > 0:
            new_avg_cost = (current_pos * current_avg_cost + cost) / (
                current_pos + quantity
            )
            self.avg_costs[symbol] = new_avg_cost

        # 更新资金和持仓
        self.cash -= round(total_cost, 2)
        self.positions[symbol] = current_pos + quantity

        # 记录交易
        self._record_trade(
            action=SignalType.BUY,
            symbol=symbol,
            price=price,
            quantity=quantity,
            time=time,
            reason=reason,
            signal_id=signal_id,
            factors=factors,
            trade_tag=trade_tag,
            position_before=current_pos,
            position_after=self.positions[symbol],
            commission=commission,
        )

        # 触发回调
        if self.on_trade:
            try:
                self.on_trade(self)
            except Exception as e:
                logger.error(f"执行交易回调失败: {e}")

        logger.info(
            f"[{time}] 买入: {self.stock_names.get(symbol, symbol)} {quantity}股 @ {price:.2f}, "
            f"成本: {cost:.2f}, 佣金: {commission:.2f}, 原因: {reason}"
        )

        return True

    def sell(
        self,
        symbol: str,
        price: float,
        quantity: int,
        time: datetime,
        reason: str,
        signal_id: Optional[str] = None,
        factors: Optional[Dict[str, Any]] = None,
        trade_tag: Optional[str] = None,
    ) -> bool:
        """
        执行卖出操作（纯资金和持仓管理）。

        Args:
            symbol: 股票代码
            price: 卖出价格
            quantity: 卖出数量
            time: 交易时间
            reason: 卖出原因
            signal_id: 信号ID（可选）
            factors: 策略因子（可选）
            trade_tag: 交易标签（可选）

        Returns:
            是否成功卖出
        """
        if quantity <= 0:
            logger.warning(f"卖出数量必须大于0: {quantity}")
            return False

        current_pos = self.positions.get(symbol, 0)
        if current_pos <= 0:
            logger.warning(f"无持仓: {symbol}")
            return False

        # 确保卖出数量不超过持仓
        quantity = min(quantity, current_pos)
        if quantity <= 0:
            return False

        # 计算收益和佣金
        revenue = quantity * price
        commission = revenue * self.commission_rate
        net_revenue = revenue - commission

        # 计算盈亏比例
        avg_cost = self.avg_costs.get(symbol, 0.0)
        profit_ratio = (price - avg_cost) / avg_cost if avg_cost > 0 else 0.0

        # 更新资金和持仓
        self.cash += round(net_revenue, 2)
        self.positions[symbol] = current_pos - quantity

        # 如果持仓为0，清空平均成本
        if self.positions[symbol] == 0:
            self.avg_costs[symbol] = 0.0

        # 记录交易
        self._record_trade(
            action=SignalType.SELL,
            symbol=symbol,
            price=price,
            quantity=quantity,
            time=time,
            reason=reason,
            signal_id=signal_id,
            factors=factors,
            trade_tag=trade_tag,
            position_before=current_pos,
            position_after=self.positions[symbol],
            commission=commission,
            profit_ratio=profit_ratio,
        )

        # 触发回调
        if self.on_trade:
            try:
                self.on_trade(self)
            except Exception as e:
                logger.error(f"执行交易回调失败: {e}")

        logger.info(
            f"[{time}] 卖出: {self.stock_names.get(symbol, symbol)} {quantity}股 @ {price:.2f}, "
            f"收益: {revenue:.2f}, 佣金: {commission:.2f}, 盈亏: {profit_ratio:.2%}, 原因: {reason}"
        )

        return True

    def _record_trade(
        self,
        action: SignalType,
        symbol: str,
        price: float,
        quantity: int,
        time: datetime,
        reason: str,
        signal_id: Optional[str],
        factors: Optional[Dict[str, Any]],
        trade_tag: Optional[str],
        position_before: int,
        position_after: int,
        commission: float,
        profit_ratio: Optional[float] = None,
    ) -> None:
        """记录交易详情"""
        trade_record = {
            "time": str(time),
            "action": action,
            "symbol": symbol,
            "price": price,
            "quantity": quantity,
            "commission": commission,
            "reason": reason,
            "signal_id": signal_id,
            "factors": factors,
            "trade_tag": trade_tag,
            "position_before": position_before,
            "position_after": position_after,
        }

        if profit_ratio is not None:
            trade_record["profit_ratio"] = profit_ratio

        self.trades.append(trade_record)

    def clear_trades(self) -> None:
        """清空交易记录"""
        self.trades.clear()

    def get_account_summary(self) -> Dict[str, Any]:
        """获取账户摘要信息"""
        return {
            "cash": self.cash,
            "total_equity": self.get_total_equity(),
            "positions": self.positions,
            "initial_capital": self.initial_capital,
            "commission_rate": self.commission_rate,
            "trade_count": len(self.trades),
            "active_positions": len([p for p in self.positions.values() if p > 0]),
        }

    def is_signal_processed(self, signal_id: str) -> bool:
        """检查信号是否已处理"""
        return signal_id in self._processed_signals

    def mark_signal_processed(self, signal_id: str) -> None:
        """标记信号为已处理"""
        self._processed_signals.add(signal_id)

    def clear_processed_signals(self) -> None:
        """清空已处理的信号记录"""
        self._processed_signals.clear()
