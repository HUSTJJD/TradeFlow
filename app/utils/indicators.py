import pandas as pd
import numpy as np


def calculate_sma(
    df: pd.DataFrame, period: int = 20, column: str = "close", out_col: str = "sma"
) -> pd.DataFrame:
    """计算简单移动平均（SMA）。"""
    df = df.sort_index()
    df[out_col] = df[column].rolling(window=period).mean()
    return df


def calculate_ema(
    df: pd.DataFrame, period: int = 20, column: str = "close", out_col: str = "ema"
) -> pd.DataFrame:
    """计算指数移动平均（EMA）。"""
    df = df.sort_index()
    df[out_col] = df[column].ewm(span=period, adjust=False).mean()
    return df


def calculate_atr(
    df: pd.DataFrame, period: int = 14, out_col: str = "atr"
) -> pd.DataFrame:
    """计算平均真实波幅（ATR）。要求 df 至少包含 high/low/close。"""
    df = df.sort_index()

    high = df["high"]
    low = df["low"]
    close = df["close"]

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    df[out_col] = tr.rolling(window=period).mean()
    return df


def calculate_donchian_channel(
    df: pd.DataFrame,
    period: int = 20,
    high_col: str = "high",
    low_col: str = "low",
    out_high: str = "donchian_high",
    out_low: str = "donchian_low",
    out_mid: str = "donchian_mid",
) -> pd.DataFrame:
    """计算 Donchian 通道（常用于趋势突破策略）。"""
    df = df.sort_index()
    df[out_high] = df[high_col].rolling(window=period).max()
    df[out_low] = df[low_col].rolling(window=period).min()
    df[out_mid] = (df[out_high] + df[out_low]) / 2
    return df


def calculate_adx(
    df: pd.DataFrame,
    period: int = 14,
    out_adx: str = "adx",
    out_plus_di: str = "plus_di",
    out_minus_di: str = "minus_di",
) -> pd.DataFrame:
    """计算 ADX（趋势强度）。要求 df 至少包含 high/low/close。"""
    df = df.sort_index().copy()

    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.rolling(window=period).mean()

    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

    diff_di = plus_di - minus_di
    sum_di = plus_di + minus_di

    dx = pd.Series(np.abs(diff_di) / sum_di, index=df.index).replace([pd.NA, pd.NaT], 0)
    dx = dx.fillna(0.0) * 100

    df[out_plus_di] = plus_di
    df[out_minus_di] = minus_di
    df[out_adx] = dx.rolling(window=period).mean()

    return df


def calculate_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    column: str = "close"
) -> pd.DataFrame:
    """
    计算 MACD 指标。

    Args:
        df: 包含价格数据的 DataFrame。
        fast: 快速 EMA 周期。
        slow: 慢速 EMA 周期。
        signal: 信号线 EMA 周期。
        column: 用于计算的价格列名。

    Returns:
        添加了 'dif', 'dea', 和 'macd' 列的 DataFrame。
    """
    # 确保数据按日期排序
    df = df.sort_index()

    # 计算 EMA
    ema_fast = df[column].ewm(span=fast, adjust=False).mean()
    ema_slow = df[column].ewm(span=slow, adjust=False).mean()

    # 计算 DIF (MACD 线)
    df["dif"] = ema_fast - ema_slow

    # 计算 DEA (信号线)
    df["dea"] = df["dif"].ewm(span=signal, adjust=False).mean()

    # 计算 MACD 柱状图
    df["macd"] = (df["dif"] - df["dea"]) * 2

    return df


def calculate_rsi(
    df: pd.DataFrame,
    period: int = 14,
    column: str = "close"
) -> pd.DataFrame:
    """
    计算 RSI 指标。

    Args:
        df: 包含价格数据的 DataFrame。
        period: RSI 计算周期。
        column: 用于计算的价格列名。

    Returns:
        添加了 'rsi' 列的 DataFrame。
    """
    df = df.sort_index()

    delta = df[column].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    # 避免除以零
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    return df


def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: int = 2,
    column: str = "close"
) -> pd.DataFrame:
    """
    计算布林带指标。

    Args:
        df: 包含价格数据的 DataFrame。
        period: 移动平均周期。
        std_dev: 标准差倍数。
        column: 用于计算的价格列名。

    Returns:
        添加了 'upper', 'middle', 'lower' 列的 DataFrame。
    """
    df = df.sort_index()

    # 计算中轨 (SMA)
    df["middle"] = df[column].rolling(window=period).mean()

    # 计算标准差
    std = df[column].rolling(window=period).std()

    # 计算上轨和下轨
    df["upper"] = df["middle"] + (std * std_dev)
    df["lower"] = df["middle"] - (std * std_dev)

    return df
