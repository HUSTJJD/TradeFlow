import sys
import os
from app import TradeFlow

# 将项目根目录添加到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    trade_flow = TradeFlow()
    trade_flow.run()