import sys
import os
import logging
from datetime import datetime
import pandas as pd

# 添加项目根目录到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from longport.openapi import QuoteContext, Config, Period
from app.core.config import global_config
from app.trading.account import Account
from app.trading.persistence import AccountPersistence
from app.utils.plotter import create_performance_chart
from app.providers.provider import fetch_history_candles

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    # 1. 加载配置
    app_key = global_config.get("longport.app_key")
    app_secret = global_config.get("longport.app_secret")
    access_token = global_config.get("longport.access_token")

    if not all([app_key, app_secret, access_token]):
        logger.error("请在 config.yaml 中配置 LongPort API 信息")
        return

    # 2. 加载账户数据
    persistence = AccountPersistence("simulate/paper_account.json")
    account = Account()
    if not persistence.load(account):
        logger.error("无法加载模拟账户数据，请先运行实盘模拟")
        return

    if not account.equity_history:
        logger.warning("账户没有权益历史记录，无法绘图")
        return

    # 3. 准备数据
    equity_curve = account.equity_history
    trades = account.trades
    
    start_date_str = str(equity_curve[0]["time"]).split(" ")[0]
    end_date_str = str(equity_curve[-1]["time"]).split(" ")[0]
    
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    logger.info(f"绘图范围: {start_date} 至 {end_date}")

    # 4. 获取基准数据
    config = Config(app_key, app_secret, access_token)
    ctx = QuoteContext(config)
    
    plot_config = global_config.get("plot", {})
    benchmarks_data = {}
    benchmarks_config = plot_config.get("benchmarks", [])
    
    if not benchmarks_config:
        # 默认基准
        benchmarks_config = [{"symbol": "HSI.HK", "name": "恒生指数"}]

    for bench_cfg in benchmarks_config:
        symbol = bench_cfg.get("symbol")
        if not symbol:
            continue
            
        try:
            # 获取基准数据
            df = fetch_history_candles(
                ctx, symbol, Period.Day, start_date, end_date, 0
            )
            if not df.empty:
                benchmarks_data[symbol] = df
                logger.info(f"已获取基准 {symbol} 数据")
        except Exception as e:
            logger.warning(f"获取基准 {symbol} 数据失败: {e}")

    # 5. 生成图表
    output_dir = plot_config.get("output_dir", "reports")
    filename = f"live_performance_{end_date_str}.html"
    
    filepath = create_performance_chart(
        equity_curve=equity_curve,
        trades=trades,
        benchmark_data=benchmarks_data,
        config=plot_config,
        output_dir=output_dir,
        filename=filename
    )
    
    if filepath:
        logger.info(f"图表已生成: {filepath}")

if __name__ == "__main__":
    main()
