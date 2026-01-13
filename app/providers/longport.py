from .provider import Provider
import logging
from datetime import date
from typing import List, Dict, Any, Optional, Type
from longport.openapi import Period, QuoteContext
from app.core import cfg
from app.utils import calculate_interval_return
import pandas as pd

logger = logging.getLogger(__name__)


class LongPortProvider(Provider):
    """长桥API数据提供器"""

    def __init__(self):
        super().__init__()
        self.quote_ctx: Optional[QuoteContext] = None

    def initialize(self, **kwargs: Any) -> bool:
        """初始化长桥数据提供器"""
        self.quote_ctx = kwargs.get("quote_ctx")
        if not self.quote_ctx:
            logger.error("LongPort QuoteContext 未设置")
            return False

        self._initialized = True
        logger.info("LongPort数据提供器初始化完成")
        return True

    def get_data(self, symbol: str, **kwargs: Any) -> Optional[pd.DataFrame]:
        """获取单个标的的数据"""
        if not self._initialized:
            if not self.initialize(**kwargs):
                return None

        period = kwargs.get("period", Period.Day)
        period_t: Type[Period] = period if isinstance(period, Type) else type(period)

        count = kwargs.get("count", 100)
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")

        try:
            if start_date and end_date:
                # 获取历史数据
                return self._get_history_candles(symbol, period_t, start_date, end_date)
            else:
                # 获取实时数据
                return self._get_realtime_candles(symbol, period_t, count)
        except Exception as e:
            logger.error(f"获取 {symbol} 数据失败: {e}")
            return None

    def get_multiple_data(
        self, symbols: List[str], **kwargs: Any
    ) -> Dict[str, pd.DataFrame]:
        """批量获取多个标的的数据"""
        if not self._initialized:
            if not self.initialize(**kwargs):
                return {}

        results = {}
        for symbol in symbols:
            data = self.get_data(symbol, **kwargs)
            if data is not None:
                results[symbol] = data

        return results

    def get_stock_names(self, symbols: List[str]) -> Dict[str, str]:
        """获取股票名称"""
        if not self._initialized or not self.quote_ctx:
            return {s: s for s in symbols}

        name_map = {}
        try:
            static_infos = self.quote_ctx.static_info(symbols)
            for info in static_infos:
                name = (
                    getattr(info, "name_cn", None)
                    or getattr(info, "name_en", None)
                    or getattr(info, "name", None)
                    or info.symbol
                )
                name_map[info.symbol] = name
        except Exception as e:
            logger.warning(f"获取股票名称失败: {e}")
            for symbol in symbols:
                name_map[symbol] = symbol

        return name_map

    def get_stock_lot_sizes(self, symbols: List[str]) -> Dict[str, int]:
        """获取股票最小交易单位"""
        if not self._initialized or not self.quote_ctx:
            return {s: 1 for s in symbols}

        lot_size_map = {}
        try:
            static_infos = self.quote_ctx.static_info(symbols)
            for info in static_infos:
                lot_size_map[info.symbol] = (
                    int(info.lot_size) if info.lot_size > 0 else 1
                )
        except Exception as e:
            logger.warning(f"获取股票最小交易单位失败: {e}")

        for symbol in symbols:
            if symbol not in lot_size_map:
                lot_size_map[symbol] = 1

        return lot_size_map

    def get_benchmark_returns(
        self, start_date: date, end_date: date
    ) -> Dict[str, float]:
        """获取基准收益率"""
        if not self._initialized or not self.quote_ctx:
            return {}

        benchmarks_config = cfg.backtest.benchmarks
        benchmarks = {}
        for symbol in benchmarks_config:
            name_map = self.get_stock_names([symbol])
            name = name_map.get(symbol, symbol)
            benchmarks[name] = symbol

        returns = {}
        from longport.openapi import AdjustType

        for name, symbol in benchmarks.items():
            try:
                candlesticks = self.quote_ctx.history_candlesticks_by_date(
                    symbol, Period.Day, AdjustType.ForwardAdjust, start_date, end_date
                )
                if candlesticks and len(candlesticks) > 0:
                    start_k = candlesticks[0]
                    end_k = candlesticks[-1]
                    start_price = float(start_k.open)
                    end_price = float(end_k.close)
                    ret = calculate_interval_return(start_price, end_price)
                    returns[name] = ret
            except Exception as e:
                logger.warning(f"获取基准 {name} ({symbol}) 失败: {e}")

        return returns

    def _get_realtime_candles(
        self, symbol: str, period: Type[Period], count: int
    ) -> Optional[pd.DataFrame]:
        """获取实时K线数据"""
        if not self.quote_ctx:
            return None
        try:
            from longport.openapi import AdjustType

            candlesticks = self.quote_ctx.candlesticks(
                symbol, period, count, AdjustType.ForwardAdjust
            )
            return self._process_candlesticks(candlesticks)
        except Exception as e:
            logger.error(f"获取实时K线数据失败 {symbol}: {e}")
            return None

    def _get_history_candles(
        self,
        symbol: str,
        period: Type[Period],
        start_date: date,
        end_date: date,
    ) -> Optional[pd.DataFrame]:
        """获取历史K线数据"""
        if not self.quote_ctx:
            return None
        try:
            from longport.openapi import AdjustType

            candlesticks = self.quote_ctx.history_candlesticks_by_date(
                symbol, period, AdjustType.ForwardAdjust, start_date, end_date
            )
            return self._process_candlesticks(candlesticks)
        except Exception as e:
            logger.error(f"获取历史K线数据失败 {symbol}: {e}")
            return None

    def _process_candlesticks(self, candlesticks: List[Any]) -> pd.DataFrame:
        """处理K线数据并转换为DataFrame"""
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
