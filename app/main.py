import logging
from longport.openapi import Config as LpConfig, QuoteContext
from app.core.config import global_config
from app.strategies import get_strategy
from app.trading.position import PositionManager
from app.core.logger import setup_logging
from app.runners.backtest import run_backtest
from app.runners.live import run_live_trading

# Initialize logging
setup_logging(global_config)
logger = logging.getLogger(__name__)


def main() -> None:
    """
    主入口点。
    """
    logger.info("正在初始化 LongPort SDK...")

    app_key = global_config.get("longport.app_key")
    app_secret = global_config.get("longport.app_secret")
    access_token = global_config.get("longport.access_token")

    if not all([app_key, app_secret, access_token]):
        logger.error("缺少 LongPort 配置。请检查 config.yaml 或环境变量。")
        return

    config = LpConfig(app_key=app_key, app_secret=app_secret, access_token=access_token)

    try:
        quote_ctx = QuoteContext(config)
    except Exception as e:
        logger.error(f"SDK 初始化失败: {e}")
        return

    strategy_name = global_config.get("strategy.name", "MACD")
    strategy_params = global_config.get("strategy.params", {})
    strategy = get_strategy(strategy_name, **strategy_params)

    # 闭市离线刷新：全市场扫描 + 打分 + 缓存
    if global_config.get("universe.refresh.enabled", False):
        from app.runners.universe_refresh import run_universe_refresh, run_universe_symbols_refresh

        logger.info("=== 开始执行闭市标的刷新任务（Step1：拉取标的代码+名称） ===")
        run_universe_symbols_refresh()

        logger.info("=== 开始执行闭市标的刷新任务（Step2：长桥拉取详细数据+打分） ===")
        run_universe_refresh(quote_ctx)
        return

    backtest_enabled = global_config.get("backtest.enabled", False)
    if backtest_enabled:
        logger.info("=== 开始回测模式 ===")
        run_backtest(quote_ctx, strategy)
        return

    # total_capital 在实盘建议生成时动态获取，这里不再需要传入
    position_ratio = global_config.get("trading.position_ratio", 0.2)
    pos_manager = PositionManager(position_ratio=position_ratio)

    run_live_trading(quote_ctx, strategy, pos_manager)


if __name__ == "__main__":
    main()
