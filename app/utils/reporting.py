import logging
from datetime import date
from typing import List, Dict, Any, Optional
from app.utils.formatting import pad_string
from app.utils.finance import calculate_interval_return

logger = logging.getLogger(__name__)


def print_backtest_summary(
    results: Dict[str, Any],
    start_date: date,
    end_date: date,
    initial_balance: float,
    benchmark_returns: Optional[Dict[str, float]] = None,
) -> None:
    """
    打印回测摘要表格。

    Args:
        results: 回测结果字典。
        start_date: 回测开始日期。
        end_date: 回测结束日期。
        initial_balance: 初始资金。
        benchmark_returns: 基准收益字典。
    """
    if not results:
        logger.warning("未生成回测结果。")
        return

    logger.info("\n" + "=" * 80)
    logger.info(f"回测期间: {start_date} 至 {end_date}")
    logger.info("-" * 80)
    logger.info(f"初始资金: {initial_balance:,.2f}")
    logger.info(f"最终权益: {results.get('final_value', 0):,.2f}")
    logger.info(f"总收益率: {results.get('total_return', 0):.2f}%")
    logger.info(f"最大回撤: {results.get('max_drawdown', 0):.2f}%")

    trades = results.get("trades", [])
    logger.info(f"总交易次数: {len(trades)}")

    if benchmark_returns:
        logger.info("-" * 80)
        logger.info("基准指数表现:")
        for k, v in benchmark_returns.items():
            logger.info(f"{k:<20}: {v:.2f}%")

    logger.info("=" * 80)

    # 提取个股表现
    logger.info("\n个股表现详情:")
    logger.info("-" * 80)
    header = f"{'代码':<10} | {'盈亏':>12} | {'ROI':>10} | {'交易次数':>8}"
    logger.info(header)
    logger.info("-" * 80)

    # 从 results 中解析个股数据
    symbol_stats = {}
    for key, value in results.items():
        if key.startswith("symbol_") and key.endswith("_pnl"):
            symbol = key.split("_")[1]
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {}
            symbol_stats[symbol]["pnl"] = value
        elif key.startswith("symbol_") and key.endswith("_roi"):
            symbol = key.split("_")[1]
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {}
            symbol_stats[symbol]["roi"] = value

    # 统计个股交易次数
    trade_counts = {}
    for trade in trades:
        sym = trade["symbol"]
        trade_counts[sym] = trade_counts.get(sym, 0) + 1

    for symbol, stats in symbol_stats.items():
        pnl = stats.get("pnl", 0.0)
        roi = stats.get("roi", 0.0)
        count = trade_counts.get(symbol, 0)

        row = f"{symbol:<10} | {pnl:>12.2f} | {roi:>9.2f}% | {count:>8}"
        logger.info(row)

    logger.info("-" * 80)
