import logging
import pandas as pd
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
import os
import json
from longport.openapi import QuoteContext, Period, AdjustType
from app.core.config import global_config
from app.utils.finance import calculate_interval_return

logger = logging.getLogger(__name__)


_UNIVERSE_CACHE_PATH = os.path.join("data", "universe", "universe_snapshot.json")
_UNIVERSE_SCORE_PATH = os.path.join("data", "universe", "universe_scores.json")

# 第一步产物：仅保存“标的代码+名称”（不依赖长桥全量标的能力）
_UNIVERSE_SYMBOLS_CN_PATH = os.path.join("data", "universe", "universe_symbols_cn.json")
_UNIVERSE_SYMBOLS_HKCONNECT_PATH = os.path.join("data", "universe", "universe_symbols_hkconnect.json")


def _load_json(path: str, default: Any) -> Any:
    if not path or not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"读取 JSON 失败 {path}: {e}")
        return default


def _save_json(path: str, data: Any) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"保存 JSON 失败 {path}: {e}")


def save_universe_symbols(path: str, items: List[Dict[str, Any]]) -> None:
    """保存标的基础清单（代码+名称）。

    items: [{"symbol": "000001.SZ", "name": "平安银行"}, ...]
    """
    payload = {
        "items": items,
    }
    _save_json(path, payload)


def load_universe_symbols(path: str) -> List[Dict[str, Any]]:
    payload = _load_json(path, {})
    items = payload.get("items", []) if isinstance(payload, dict) else []
    if not isinstance(items, list):
        return []
    return items


def save_cn_universe_symbols(items: List[Dict[str, Any]]) -> None:
    save_universe_symbols(_UNIVERSE_SYMBOLS_CN_PATH, items)


def load_cn_universe_symbols() -> List[Dict[str, Any]]:
    return load_universe_symbols(_UNIVERSE_SYMBOLS_CN_PATH)


def save_hkconnect_universe_symbols(items: List[Dict[str, Any]]) -> None:
    save_universe_symbols(_UNIVERSE_SYMBOLS_HKCONNECT_PATH, items)


def load_hkconnect_universe_symbols() -> List[Dict[str, Any]]:
    return load_universe_symbols(_UNIVERSE_SYMBOLS_HKCONNECT_PATH)


def get_universe_symbols_paths() -> Dict[str, str]:
    return {
        "CN": _UNIVERSE_SYMBOLS_CN_PATH,
        "HKCONNECT": _UNIVERSE_SYMBOLS_HKCONNECT_PATH,
    }


def _select_top_symbols(
    candidates: List[Dict[str, Any]],
    max_symbols: int,
    one_per_industry: bool,
) -> List[str]:
    selected: List[str] = []
    used_industries = set()

    for item in sorted(candidates, key=lambda x: float(x.get("score", 0)), reverse=True):
        symbol = item.get("symbol")
        if not symbol:
            continue

        industry = item.get("industry") or "UNKNOWN"
        if one_per_industry and industry in used_industries:
            continue

        selected.append(symbol)
        used_industries.add(industry)

        if len(selected) >= max_symbols:
            break

    return selected


def get_stock_pool() -> List[str]:
    """获取需要监控的股票代码列表。

    说明：
    - 不再通过 config.yaml 固定配置标的；改为从本地缓存的“全市场扫描 + 打分”结果中自动选择。
    - 规则：最多 5 个标的；默认每个行业只选 1 个。

    需要先离线刷新：见 `refresh_universe_cache()`。
    """

    selector_cfg = global_config.get("universe.selector", {}) or {}
    max_symbols = int(selector_cfg.get("max_symbols", 5))
    one_per_industry = bool(selector_cfg.get("one_per_industry", True))

    scores = _load_json(_UNIVERSE_SCORE_PATH, {})
    candidates = scores.get("candidates", []) if isinstance(scores, dict) else []

    symbols = _select_top_symbols(candidates, max_symbols=max_symbols, one_per_industry=one_per_industry)

    logger.info(f"动态股票池: {len(symbols)} 只股票")
    if not symbols:
        logger.warning(
            "动态股票池为空：请先在闭市时运行 universe 刷新任务（拉取全市场数据并打分写入本地缓存）。"
        )

    return symbols


def refresh_universe_cache(snapshot: Dict[str, Any], scores: Dict[str, Any]) -> None:
    """将闭市扫描得到的全市场快照与打分结果写入本地缓存。"""
    _save_json(_UNIVERSE_CACHE_PATH, snapshot)
    _save_json(_UNIVERSE_SCORE_PATH, scores)


def get_stock_names(quote_ctx: QuoteContext, symbols: List[str]) -> Dict[str, str]:
    """
    获取指定股票代码的股票名称。

    Args:
        quote_ctx: LongPort QuoteContext 对象。
        symbols: 股票代码列表。

    Returns:
        股票代码到股票名称的映射字典。
    """
    name_map = {}
    try:
        # 获取包含名称的静态信息
        static_infos = quote_ctx.static_info(symbols)
        for info in static_infos:
            # 优先使用中文名，其次英文名，最后使用代码
            name = (
                getattr(info, "name_cn", None)
                or getattr(info, "name_en", None)
                or getattr(info, "name", None)
                or info.symbol
            )
            name_map[info.symbol] = name
    except Exception as e:
        logger.warning(f"获取股票名称失败: {e}")
        # 失败时使用代码作为名称
        for symbol in symbols:
            name_map[symbol] = symbol

    return name_map


def get_stock_lot_sizes(quote_ctx: QuoteContext, symbols: List[str]) -> Dict[str, int]:
    """
    获取指定股票代码的最小交易单位（lot size）。

    Args:
        quote_ctx: LongPort QuoteContext 对象。
        symbols: 股票代码列表。

    Returns:
        股票代码到最小交易单位的映射字典。默认为 1。
    """
    lot_size_map = {}
    try:
        static_infos = quote_ctx.static_info(symbols)
        for info in static_infos:
            lot_size_map[info.symbol] = int(info.lot_size) if info.lot_size > 0 else 1
    except Exception as e:
        logger.warning(f"获取股票最小交易单位失败: {e}")
        
    # 确保所有 symbol 都有值，默认为 1
    for symbol in symbols:
        if symbol not in lot_size_map:
            lot_size_map[symbol] = 1
            
    return lot_size_map


def get_period(timeframe_str: str) -> Period:
    """
    将时间周期字符串转换为 LongPort Period 枚举。
    """
    mapping = {
        "1m": Period.Min_1,
        "5m": Period.Min_5,
        "15m": Period.Min_15,
        "30m": Period.Min_30,
        "60m": Period.Min_60,
        "1d": Period.Day,
        "1w": Period.Week,
        "1M": Period.Month,
    }
    return mapping.get(timeframe_str, Period.Min_15)


def _process_candlesticks(candlesticks: List[Any]) -> pd.DataFrame:
    """
    处理 K 线数据列表并转换为 DataFrame。
    
    Args:
        candlesticks: LongPort K 线对象列表。
        
    Returns:
        包含 'time', 'open', 'high', 'low', 'close', 'volume' 的 DataFrame。
    """
    if not candlesticks:
        return pd.DataFrame()

    data = []
    for k in candlesticks:
        data.append(
            {
                "time": k.timestamp,
                "open": float(k.open),
                "high": float(k.high),
                "low": float(k.low),
                "close": float(k.close),
                "volume": int(k.volume),
            }
        )

    df = pd.DataFrame(data)
    if not df.empty:
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("time", inplace=True)
    return df


def fetch_candles(
    quote_ctx: QuoteContext, symbol: str, period: Period, count: int
) -> pd.DataFrame:
    """
    获取K线数据并转换为 DataFrame。

    Args:
        quote_ctx: LongPort QuoteContext 对象。
        symbol: 股票代码。
        period: K线周期。
        count: 获取的K线数量。

    Returns:
        包含 'time', 'open', 'high', 'low', 'close', 'volume' 的 DataFrame。
    """
    try:
        candlesticks = quote_ctx.candlesticks(
            symbol, period, count, AdjustType.ForwardAdjust
        )
        return _process_candlesticks(candlesticks)
    except Exception as e:
        logger.error(f"获取 {symbol} 的K线数据失败: {e}")
        return pd.DataFrame()


def get_benchmark_returns(
    quote_ctx: QuoteContext, start_date: date, end_date: date
) -> Dict[str, float]:
    """
    计算特定时间段内的基准收益率。
    """
    benchmarks_config = global_config.get("backtest.benchmarks")

    benchmarks = {}
    if isinstance(benchmarks_config, list):
        name_map = get_stock_names(quote_ctx, benchmarks_config)
        for symbol in benchmarks_config:
            name = name_map.get(symbol, symbol)
            benchmarks[name] = symbol
    else:
        logger.warning(f"基准配置必须是列表格式，当前格式: {type(benchmarks_config)}")
        return {}

    returns = {}

    for name, symbol in benchmarks.items():
        try:
            candlesticks = quote_ctx.history_candlesticks_by_date(
                symbol, Period.Day, AdjustType.ForwardAdjust, start_date, end_date
            )
            if candlesticks and len(candlesticks) > 0:
                start_k = candlesticks[0]
                end_k = candlesticks[-1]

                # 使用开盘价作为起始价以捕捉第一天的波动
                start_price = float(start_k.open)
                end_price = float(end_k.close)

                ret = calculate_interval_return(start_price, end_price)
                returns[name] = ret
        except Exception as e:
            logger.warning(f"获取基准 {name} ({symbol}) 失败: {e}")

    return returns


def fetch_history_candles(
    quote_ctx: QuoteContext,
    symbol: str,
    period: Period,
    start_date: date,
    end_date: date,
    warmup_days: int = 0,
) -> pd.DataFrame:
    """
    获取指定日期范围的历史K线数据，支持预热期。

    Args:
        quote_ctx: LongPort QuoteContext 对象。
        symbol: 股票代码。
        period: K线周期。
        start_date: 开始日期。
        end_date: 结束日期。
        warmup_days: 预热天数，将在 start_date 之前获取额外的数据。

    Returns:
        包含历史数据的 DataFrame。
    """
    pre_start_date = start_date - timedelta(days=warmup_days)
    
    try:
        candlesticks = quote_ctx.history_candlesticks_by_date(
            symbol, period, AdjustType.ForwardAdjust, pre_start_date, end_date
        )

        df = _process_candlesticks(candlesticks)
        
        if not df.empty:
            # 确保不包含 end_date 之后的数据 (双重保险)
            end_ts = pd.Timestamp(end_date) + pd.Timedelta(days=1)
            df = df[df.index < end_ts]
            
        return df
    except Exception as e:
        logger.error(f"获取 {symbol} 的历史K线数据失败: {e}")
        return pd.DataFrame()
