from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, cast, Iterable
from datetime import datetime
import pandas as pd
import logging
from longport.openapi import QuoteContext, Period
from app.core import global_config, singleton_threadsafe, SignalType, TradeMode
from app.strategies import Strategy
from app.trading.account import Account
from app.providers import create_provider, Provider

logger = logging.getLogger(__name__)

class Engine(ABC):
    """策略执行引擎抽象基类，定义统一的策略执行接口。"""

    def __init__(self):

        # 初始化数据提供器
        self.provider = create_provider()

        # 仓位管理配置
        self.position_sizing_config = global_config.trading.position_sizing
        self.max_position_ratio = self.position_sizing_config.max_position_ratio
        self.risk_per_trade = self.position_sizing_config.risk_per_trade
        self.min_rebalance_ratio = self.position_sizing_config.min_rebalance_ratio

        self.equity_curve: List[Dict[str, Any]] = []
        self.t_daily_counts: Dict[str, Dict[str, Any]] = {}
        self.t_max_per_symbol_per_day = 1
        self.lot_sizes: Dict[str, int] = {}
        self.stock_names: Dict[str, str] = {}

        self.create_account()

    def initialize(self, symbols: List[str], quote_ctx: QuoteContext) -> bool:
        """初始化引擎"""
        try:
            self.stock_names = self.provider.get_stock_names(symbols)
            if not self.lot_sizes:
                self.lot_sizes = self.provider.get_stock_lot_sizes(symbols)
            return True
        except Exception as e:
            logger.error(f"引擎初始化失败: {e}")
            return False

    @abstractmethod
    def create_account(self) -> None:
        """交易账户"""
        # 默认实现，子类可覆盖
        self._account = Account(initial_balance=self.initial_capital)

    @abstractmethod
    def run(self) -> Dict[str, Any]:
        """运行策略执行引擎"""
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """清理资源"""
        self.create_account()
        logger.info("策略执行引擎已清理")

    def _allow_t_trade(self, symbol: str, current_time: datetime) -> bool:
        """做T频控：仅限制 trade_tag==\"T\" 的信号。"""
        date_str = str(current_time.date())
        daily = self.t_daily_counts.get(symbol)
        if daily is None or daily.get("date") != date_str:
            daily = {"date": date_str, "count": 0}
            self.t_daily_counts[symbol] = daily

        return int(daily.get("count", 0)) < self.t_max_per_symbol_per_day

    def _mark_t_trade(self, symbol: str, current_time: datetime) -> None:
        """标记做T交易"""
        date_str = str(current_time.date())
        daily = self.t_daily_counts.get(symbol)
        if daily is None or daily.get("date") != date_str:
            daily = {"date": date_str, "count": 0}
            self.t_daily_counts[symbol] = daily
        daily["count"] = int(daily.get("count", 0)) + 1

    def process_signal(
        self,
        symbol: str,
        signal: Dict[str, Any],
        current_time: datetime,
        current_price: float,
    ) -> Dict[str, Any]:
        """处理单个信号"""

        # 更新价格
        self._account.update_price(symbol, current_price)

        # 做T频控检查
        trade_tag = signal.get("trade_tag")
        if trade_tag == "T" and not self._allow_t_trade(symbol, current_time):
            return {"status": "SKIPPED", "reason": "做T频控限制"}

        # 执行交易
        result = self._execute_trade(signal, symbol, current_time, current_price)

        # 记录做T交易
        if trade_tag == "T" and result.get("status") == "SUCCESS":
            self._mark_t_trade(symbol, current_time)

        return result

    def _execute_trade(
        self,
        signal: Dict[str, Any],
        symbol: str,
        timestamp: datetime,
        price: float,
    ) -> Dict[str, Any]:
        """执行交易信号，统一处理买入和卖出逻辑。"""
        action = signal.get("action")
        reason = str(signal.get("reason", ""))
        factors = signal.get("factors", {})
        if not isinstance(factors, dict):
            factors = {}
        trade_tag = signal.get("trade_tag")

        signal_id = f"{symbol}_{timestamp.strftime('%Y%m%d%H%M%S')}_{action}"

        if action == SignalType.BUY:
            return self._execute_buy(
                signal_id, symbol, timestamp, price, reason, factors, trade_tag
            )
        elif action == SignalType.SELL:
            return self._execute_sell(
                signal_id, symbol, timestamp, price, reason, factors, trade_tag
            )
        else:
            return {
                "status": "SKIPPED",
                "action": action,
                "symbol": symbol,
                "price": price,
                "time": timestamp,
                "quantity": 0,
                "msg": "未知动作",
                "signal_id": signal_id,
            }

    def _execute_buy(
        self, signal_id, symbol, timestamp, price, reason, factors, trade_tag
    ):
        lot_size = self.lot_sizes.get(symbol, 1)
        current_equity = self._account.get_total_equity()
        current_position = self._account.positions.get(symbol, 0)

        quantity = self.calculate_order_quantity(
            action=SignalType.BUY,
            current_position=current_position,
            price=price,
            total_equity=current_equity,
            available_cash=self._account.cash,
            lot_size=lot_size,
            signal={"trade_tag": trade_tag, **factors},
        )

        quantity = self._normalize_quantity(symbol, quantity)

        if quantity <= 0:
            return {
                "status": "SKIPPED",
                "action": SignalType.BUY,
                "symbol": symbol,
                "price": price,
                "time": timestamp,
                "quantity": 0,
                "msg": "计算数量为0",
                "signal_id": signal_id,
            }

        success = self._account.buy(
            symbol=symbol,
            price=price,
            quantity=quantity,
            time=timestamp,
            reason=reason,
            signal_id=signal_id,
            factors=factors,
            trade_tag=trade_tag,
        )

        if success:
            return {
                "status": "SUCCESS",
                "action": SignalType.BUY,
                "symbol": symbol,
                "price": price,
                "time": timestamp,
                "quantity": quantity,
                "msg": f"买入成功: {quantity}股",
                "signal_id": signal_id,
            }
        else:
            return {
                "status": "FAILED",
                "action": SignalType.BUY,
                "symbol": symbol,
                "price": price,
                "time": timestamp,
                "quantity": 0,
                "msg": "买入失败: 资金不足",
                "signal_id": signal_id,
            }

    def _execute_sell(
        self, signal_id, symbol, timestamp, price, reason, factors, trade_tag
    ):
        current_position = self._account.positions.get(symbol, 0)
        if current_position <= 0:
            return {
                "status": "FAILED",
                "action": SignalType.SELL,
                "symbol": symbol,
                "price": price,
                "time": timestamp,
                "quantity": 0,
                "msg": "无持仓",
                "signal_id": signal_id,
            }

        lot_size = self.lot_sizes.get(symbol, 1)
        current_equity = self._account.get_total_equity()

        quantity = self.calculate_order_quantity(
            action=SignalType.SELL,
            current_position=current_position,
            price=price,
            total_equity=current_equity,
            available_cash=self._account.cash,
            lot_size=lot_size,
            signal={"trade_tag": trade_tag, **factors},
        )

        quantity = self._normalize_quantity(symbol, quantity)

        if quantity <= 0:
            return {
                "status": "SKIPPED",
                "action": SignalType.SELL,
                "symbol": symbol,
                "price": price,
                "time": timestamp,
                "quantity": 0,
                "msg": "计算数量为0",
                "signal_id": signal_id,
            }

        success = self._account.sell(
            symbol=symbol,
            price=price,
            quantity=quantity,
            time=timestamp,
            reason=reason,
            signal_id=signal_id,
            factors=factors,
            trade_tag=trade_tag,
        )

        if success:
            return {
                "status": "SUCCESS",
                "action": SignalType.SELL,
                "symbol": symbol,
                "price": price,
                "time": timestamp,
                "quantity": quantity,
                "msg": f"卖出成功: {quantity}股",
                "signal_id": signal_id,
            }
        else:
            return {
                "status": "FAILED",
                "action": SignalType.SELL,
                "symbol": symbol,
                "price": price,
                "time": timestamp,
                "quantity": 0,
                "msg": "卖出失败",
                "signal_id": signal_id,
            }

    def _normalize_quantity(self, symbol: str, quantity: int) -> int:
        """数量标准化（按最小交易单位）"""
        lot_size = self.lot_sizes.get(symbol, 1)
        if lot_size > 1:
            return (quantity // lot_size) * lot_size
        return quantity

    def calculate_target_position_ratio(self, signal: Dict[str, Any]) -> float:
        """根据策略因子计算目标仓位比例。"""
        factors = signal.get("factors") or {}
        price = float(factors.get("close") or 0.0)
        atr = float(factors.get("atr") or 0.0)

        # 缺少波动信息时，退化为固定仓位
        if price <= 0 or atr <= 0:
            return min(self.position_ratio, self.max_position_ratio)

        vol_ratio = atr / price
        if vol_ratio <= 0:
            return min(self.position_ratio, self.max_position_ratio)

        # 简化的波动缩放：波动越大，目标仓位越小
        scaled = self.max_position_ratio * (0.02 / max(vol_ratio, 0.005))
        return max(0.0, min(self.max_position_ratio, scaled))

    def calculate_order_quantity(
        self,
        action: SignalType,
        current_position: int,
        price: float,
        total_equity: float,
        available_cash: float,
        lot_size: int = 1,
        signal: Optional[Dict[str, Any]] = None,
    ) -> int:
        """把 BUY/SELL 信号转换为具体下单数量（支持加/减仓）。"""
        signal = signal or {}

        if price <= 0 or total_equity <= 0:
            return 0

        target_shares = signal.get("target_shares")
        if isinstance(target_shares, (int, float)):
            target_pos = max(0, int(target_shares))
        else:
            target_ratio = signal.get("target_position_ratio")
            if not isinstance(target_ratio, (int, float)):
                target_ratio = self.calculate_target_position_ratio(signal)

            target_amount = float(total_equity) * float(target_ratio)
            target_pos = int(target_amount / price)

        # 使用内部的 _normalize_quantity 逻辑，但这里需要传入 symbol，或者我们直接用 lot_size 计算
        # 为了复用 _normalize_quantity，我们需要 symbol，但这里参数只有 lot_size
        # 我们可以简单实现一个基于 lot_size 的标准化
        if lot_size > 1:
            target_pos = (target_pos // lot_size) * lot_size

        if action == SignalType.BUY:
            delta = target_pos - current_position
            if delta <= 0:
                return 0

            # 现金约束
            max_affordable = int(available_cash / price)
            if lot_size > 1:
                max_affordable = (max_affordable // lot_size) * lot_size
            delta = min(delta, max_affordable)

        elif action == SignalType.SELL:
            # 默认 SELL 视为降低仓位。若策略未指定目标仓位，则清仓。
            if "target_shares" in signal or "target_position_ratio" in signal:
                delta = current_position - target_pos
            else:
                delta = current_position

            if delta <= 0:
                return 0

            delta = min(delta, current_position)
            if lot_size > 1:
                delta = (delta // lot_size) * lot_size

        else:
            return 0

        # 低频阈值：变化不足则不交易
        min_change = int(max(1, current_position) * self.min_rebalance_ratio)
        if lot_size > 1:
            min_change = (min_change // lot_size) * lot_size

        if signal.get("trade_tag") == "T":
            # 做T更严格一些
            t_threshold = int(max(1, current_position) * 0.10)
            if lot_size > 1:
                t_threshold = (t_threshold // lot_size) * lot_size
            min_change = max(min_change, t_threshold)

        if delta < min_change:
            return 0

        return int(delta)

    def record_equity(self, timestamp: datetime) -> None:
        """记录当前权益"""
        equity = self._account.get_total_equity()
        self.equity_curve.append({"time": timestamp, "equity": equity})

    def get_performance(self) -> Dict[str, Any]:
        """获取性能指标"""
        if not self.equity_curve:
            return {}
        df_equity = pd.DataFrame(self.equity_curve).set_index("time")
        final_equity = float(df_equity.iloc[-1]["equity"])
        total_return = (final_equity - self.initial_capital) / self.initial_capital

        df_equity["max_equity"] = df_equity["equity"].cummax()
        df_equity["drawdown"] = (
            df_equity["equity"] - df_equity["max_equity"]
        ) / df_equity["max_equity"]
        max_drawdown = float(df_equity["drawdown"].min())

        trade_stats = self._account.get_trade_stats()

        return {
            "initial_capital": self.initial_capital,
            "final_value": final_equity,
            "total_return": total_return * 100,
            "max_drawdown": max_drawdown * 100,
            **trade_stats,
        }

    def get_results(self) -> Dict[str, Any]:
        """获取完整结果"""
        return {
            "trades": self._account.trades,
            "equity_curve": self.equity_curve,
            "performance": self.get_performance(),
            "positions": self._account.positions,
            "cash": self._account.cash,
        }
