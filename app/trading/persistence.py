import json
import os
import logging
from typing import Optional
from app.trading.account import PaperAccount

logger = logging.getLogger(__name__)

class AccountPersistence:
    """
    负责 PaperAccount 的持久化（加载和保存）。
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self, account: PaperAccount) -> bool:
        """
        从文件加载账户状态到 account 对象中。
        """
        if not self.file_path or not os.path.exists(self.file_path):
            return False

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                account.cash = data.get("cash", account.initial_capital)
                account.initial_capital = data.get("initial_capital", account.initial_capital)
                account.positions = data.get("positions", {})
                account.avg_costs = data.get("avg_costs", {})
                account.trades = data.get("trades", [])
                account.equity_history = data.get("equity_history", [])
                # 加载已处理的信号ID
                account.clear_processed_signals()
                for signal_id in data.get("processed_signals", []):
                    if signal_id:
                        account.mark_signal_processed(str(signal_id))
                # latest_prices 不持久化
                account.latest_prices = {}
                
                logger.info(
                    f"成功加载账户状态: 现金={account.cash}, 持仓={account.positions}, 交易记录数={len(account.trades)}"
                )
                return True
        except Exception as e:
            logger.error(f"加载账户状态失败: {e}")
            return False

    def save(self, account: PaperAccount) -> None:
        """
        将 account 对象的状态保存到文件。
        """
        if not self.file_path:
            return

        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

            data = {
                "cash": account.cash,
                "initial_capital": account.initial_capital,
                "positions": account.positions,
                "avg_costs": account.avg_costs,
                "trades": account.trades,
                "equity_history": account.equity_history,
                "processed_signals": list(account._processed_signals),
            }
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存账户状态失败: {e}")
