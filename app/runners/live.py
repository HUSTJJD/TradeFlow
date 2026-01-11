import time
import logging
from datetime import datetime
from longport.openapi import QuoteContext, Period
from app.core.config import global_config
from app.strategies import Strategy
from app.trading.position import PositionManager
from app.utils.notifier import notifier
from app.trading.account import PaperAccount
from app.trading.persistence import AccountPersistence
from app.trading.executor import TradeExecutor
from app.core.setup import initialize_trading_context, get_strategy_config
from app.core.constants import SignalType
from app.data.provider import fetch_candles, get_stock_lot_sizes

logger = logging.getLogger(__name__)


def run_live_trading(
    quote_ctx: QuoteContext, strategy: Strategy, pos_manager: PositionManager
) -> None:
    """
    执行实盘交易监控循环。
    """
    # 使用通用初始化函数
    symbols, stock_names = initialize_trading_context(quote_ctx)
    if not symbols:
        return

    # 获取股票最小交易单位
    lot_sizes = get_stock_lot_sizes(quote_ctx, symbols)

    # 初始化模拟账户
    initial_balance = global_config.get("trading.initial_balance", 100000.0)

    # 初始化持久化
    persistence = AccountPersistence("simulate/paper_account.json")

    # 定义保存回调
    def save_account(acc):
        persistence.save(acc)

    account = PaperAccount(initial_capital=initial_balance, on_trade=save_account)
    account.set_stock_names(stock_names)

    # 尝试加载之前的状态
    persistence.load(account)

    logger.info(
        f"模拟账户已初始化。当前可用资金: {account.cash:.2f}, 总权益: {account.get_total_equity():.2f}"
    )
    if account.positions:
        logger.info(f"当前持仓: {account.positions}")

    # 初始化交易执行器
    executor = TradeExecutor(account, pos_manager)
    executor.set_lot_sizes(lot_sizes)

    logger.info("开始实盘监控...")

    last_signals = {symbol: SignalType.HOLD for symbol in symbols}

    # 做T频控（每日每股 1-2 次）
    t_max_per_symbol_per_day = int(global_config.get("strategy.t.max_trades_per_symbol_per_day", 2))
    t_daily_counts = {symbol: {"date": None, "count": 0} for symbol in symbols}

    # 获取策略配置
    strat_config = get_strategy_config()
    period = strat_config["period"]
    history_count = strat_config["history_count"]

    interval = global_config.get("monitor.interval", 60)
    request_delay = global_config.get("monitor.request_delay", 0.5)

    try:
        while True:
            logger.info(f"开始新的扫描周期: {datetime.now()}")

            for symbol in symbols:
                stock_name = stock_names.get(symbol, symbol)
                df = fetch_candles(quote_ctx, symbol, period, history_count)

                if df.empty:
                    continue

                current_price = float(df.iloc[-1]["close"])
                # 使用 K 线时间作为信号时间，避免重复触发
                signal_time = df.index[-1].to_pydatetime()

                time_diff = datetime.now() - signal_time
                is_outdated = False
                period_seconds = 60  # 默认 1m
                if period == Period.Min_5:
                    period_seconds = 300
                elif period == Period.Min_15:
                    period_seconds = 900
                elif period == Period.Min_30:
                    period_seconds = 1800
                elif period == Period.Min_60:
                    period_seconds = 3600
                elif period == Period.Day:
                    period_seconds = 86400

                if time_diff.total_seconds() > (period_seconds * 2 + 300):
                    is_outdated = True
                    logger.debug(f"{symbol} 数据滞后 ({time_diff})，市场可能休市")

                if is_outdated:
                    continue

                account.update_price(symbol, current_price)

                account.record_equity(signal_time.date(), account.get_total_equity())
                persistence.save(account)

                signal = strategy.analyze(symbol, df)
                if "price" not in signal:
                    signal["price"] = current_price

                # 做T频控：仅限制 trade_tag=="T" 的信号
                trade_tag = signal.get("trade_tag")
                if trade_tag == "T":
                    today_str = str(signal_time.date())
                    daily = t_daily_counts[symbol]
                    if daily["date"] != today_str:
                        daily["date"] = today_str
                        daily["count"] = 0

                    if daily["count"] >= t_max_per_symbol_per_day:
                        continue

                if signal["action"] in [SignalType.BUY, SignalType.SELL]:
                    result = executor.execute(signal, symbol, signal_time, current_price)
                    trade_info = result["msg"]

                    if result["status"] == "SKIPPED":
                        if signal["action"] != last_signals[symbol]:
                            logger.info(
                                f"信号已存在但动作改变 (可能重启导致): {symbol} {signal['action']}"
                            )
                            last_signals[symbol] = signal["action"]
                        continue

                    if trade_tag == "T" and result["status"] == "SUCCESS":
                        t_daily_counts[symbol]["count"] += 1

                    pos_suggestion = pos_manager.get_position_suggestion(
                        signal, current_price, account.get_total_equity()
                    )

                    trade_stats = account.get_trade_stats()
                    win_rate_str = (
                        f"{trade_stats['win_rate']*100:.1f}%" if trade_stats["total_trades"] > 0 else "N/A"
                    )

                    title = f"【信号】{stock_name} ({symbol}) {signal['action']}"
                    content = (
                        f"代码: {symbol}<br>"
                        f"名称: {stock_name}<br>"
                        f"时间: {signal_time}<br>"
                        f"动作: {signal['action']}<br>"
                        f"标签: {trade_tag or 'N/A'}<br>"
                        f"价格: {current_price}<br>"
                        f"原因: {signal['reason']}<br>"
                        f"建议: {pos_suggestion}<br>"
                        f"模拟盘: {trade_info}<br>"
                        f"账户状态: 现金={account.cash:.2f}, 总权益={account.get_total_equity():.2f}<br>"
                        f"胜率: {win_rate_str} ({trade_stats['winning_trades']}/{trade_stats['total_trades']})"
                    )

                    logger.info(f"触发信号: {title}")
                    notifier.send_message(title, content)

                    last_signals[symbol] = signal["action"]

                time.sleep(request_delay)

            logger.info(f"周期完成。等待 {interval} 秒...")
            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("程序由用户停止。")
    except Exception as e:
        logger.error(f"实盘交易中发生未处理的异常: {e}")
