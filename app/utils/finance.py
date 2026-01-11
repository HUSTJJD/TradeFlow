from typing import Optional
import pandas as pd


def calculate_interval_return(start_price: float, end_price: float) -> float:
    """
    计算区间收益率。

    Args:
        start_price: 起始价格
        end_price: 结束价格

    Returns:
        float: 收益率百分比，如果起始价格 <= 0 则返回 0.0
    """
    if start_price <= 0:
        return 0.0
    return (end_price - start_price) / start_price * 100


def get_price_range(df: pd.DataFrame) -> tuple[float, float]:
    """
    从 DataFrame 获取起止价格。
    假设 DataFrame 包含 'open' 和 'close' 列，且按时间排序。

    Returns:
        tuple[float, float]: (start_price, end_price)
    """
    if df.empty:
        return 0.0, 0.0

    start_price = float(df.iloc[0]["open"])
    end_price = float(df.iloc[-1]["close"])
    return start_price, end_price
