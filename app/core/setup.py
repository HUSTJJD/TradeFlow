import logging
from typing import List, Dict, Tuple, Any
from longport.openapi import QuoteContext
from app.core.config import global_config
from app.data.provider import get_stock_pool, get_stock_names, get_period

logger = logging.getLogger(__name__)

def initialize_trading_context(quote_ctx: QuoteContext) -> Tuple[List[str], Dict[str, str]]:
    """
    初始化交易上下文：获取股票池和股票名称。
    """
    symbols = get_stock_pool()
    if not symbols:
        logger.warning("股票池为空。请先执行闭市标的扫描与打分任务生成本地缓存。")
        return [], {}

    logger.info("正在获取股票名称...")
    stock_names = get_stock_names(quote_ctx, symbols)
    
    return symbols, stock_names

def get_strategy_config() -> Dict[str, Any]:
    """
    获取策略相关的通用配置。
    """
    timeframe = global_config.get("strategy.timeframe", "15m")
    period = get_period(timeframe)
    history_count = global_config.get("strategy.history_count", 100)
    
    return {
        "timeframe": timeframe,
        "period": period,
        "history_count": history_count
    }
