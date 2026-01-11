from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Type
from datetime import date, timedelta
import pandas as pd
import logging
from longport.openapi import QuoteContext, Period

logger = logging.getLogger(__name__)


class Provider(ABC):
    """数据提供器抽象基类，定义统一的数据访问接口。"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._initialized = False
    
    @abstractmethod
    def initialize(self, **kwargs: Any) -> bool:
        """初始化数据提供器"""
        pass
    
    @abstractmethod
    def get_data(self, symbol: str, **kwargs: Any) -> Optional[pd.DataFrame]:
        """获取指定标的的数据"""
        pass
    
    @abstractmethod
    def get_multiple_data(self, symbols: List[str], **kwargs: Any) -> Dict[str, pd.DataFrame]:
        """批量获取多个标的的数据"""
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """获取数据提供器信息"""
        return {
            "name": self.name,
            "description": self.description,
            "initialized": self._initialized
        }
    
    def cleanup(self) -> None:
        """清理资源"""
        self._initialized = False


class LongPortProvider(Provider):
    """长桥API数据提供器"""
    
    def __init__(self):
        super().__init__("LongPort", "长桥API数据提供器，支持实时和历史数据获取")
    
    def initialize(self, **kwargs: Any) -> bool:
        """初始化长桥数据提供器"""

        if not self.quote_ctx:
            logger.error("LongPort QuoteContext 未设置")
            return False
        
        self._initialized = True
        logger.info("LongPort数据提供器初始化完成")
        return True
    
    def get_data(self, symbol: str, **kwargs: Any) -> Optional[pd.DataFrame]:
        """获取单个标的的数据"""
        if not self._initialized:
            if not self.initialize():
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
    
    def get_multiple_data(self, symbols: List[str], **kwargs: Any) -> Dict[str, pd.DataFrame]:
        """批量获取多个标的的数据"""
        if not self._initialized:
            if not self.initialize():
                return {}
        
        results = {}
        for symbol in symbols:
            data = self.get_data(symbol, **kwargs)
            if data is not None:
                results[symbol] = data
        
        return results
    
    def _get_realtime_candles(self, symbol: str, period: Type[Period], count: int) -> Optional[pd.DataFrame]:
        """获取实时K线数据"""
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
            data.append({
                "time": k.timestamp,
                "open": float(k.open),
                "high": float(k.high),
                "low": float(k.low),
                "close": float(k.close),
                "volume": int(k.volume),
            })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df["time"] = pd.to_datetime(df["time"], unit="s")
            df.set_index("time", inplace=True)
        return df


class ExchangeDataProvider(Provider):
    """交易所官方接口数据提供器"""
    
    def __init__(self):
        super().__init__("Exchange", "交易所官方接口数据提供器，支持沪深交易所和港股通数据")
        self._session = None

    def initialize(self, **kwargs: Any) -> bool:
        """初始化交易所数据提供器"""
        if self._initialized:
            return True
        
        try:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "*/*"
            })
            self._initialized = True
            logger.info("交易所数据提供器初始化完成")
            return True
        except Exception as e:
            logger.error(f"初始化交易所数据提供器失败: {e}")
            return False

    def get_data(self, symbol: str, **kwargs: Any) -> Optional[pd.DataFrame]:
        """获取交易所数据（暂不支持单个标的查询）"""
        logger.warning("交易所数据提供器不支持单个标的查询，请使用批量接口")
        return None

    def get_multiple_data(self, symbols: List[str], **kwargs: Any) -> Dict[str, pd.DataFrame]:
        """批量获取交易所数据（暂不支持）"""
        logger.warning("交易所数据提供器暂不支持批量数据获取")
        return {}

    def get_universe_symbols(self, market: str, **kwargs: Any) -> List[Dict[str, Any]]:
        """获取指定市场的标的清单"""
        # Always ensure initialized (callers may instantiate provider directly).
        if not self._initialized:
            if not self.initialize():
                return []

        try:
            if market.upper() == "CN":
                return self._get_cn_universe_symbols(**kwargs)
            elif market.upper() == "HKCONNECT":
                return self._get_hkconnect_universe_symbols(**kwargs)
            else:
                logger.error(f"不支持的市场类型: {market}")
                return []
        except Exception as e:
            logger.error(f"获取 {market} 标的清单失败: {e}")
            return []

    def _get_cn_universe_symbols(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """获取A股标的清单（上交所主板/科创板 + 深交所）"""
        if self._session is None:
            return []

        from app.core.config import global_config

        api_cfg = global_config.get("api", {}) or {}
        sse_cfg = api_cfg.get("sse_stocks", {}) or {}
        sse_main_url = str(sse_cfg.get("main_board", "") or "")
        sse_star_url = str(sse_cfg.get("star_market", "") or "")
        szse_url = str(api_cfg.get("szse_stocks", "") or "")

        items: List[Dict[str, Any]] = []

        def _append(symbol: str, name: str) -> None:
            symbol = (symbol or "").strip()
            if not symbol:
                return
            name = (name or "").strip() or symbol
            items.append({"symbol": symbol, "name": name})

        def _try_parse_excel(content: bytes) -> Optional[pd.DataFrame]:
            import io

            try:
                return pd.read_excel(io.BytesIO(content))
            except Exception:
                return None

        def _parse_sse_response(content: bytes) -> List[Dict[str, Any]]:
            """SSE 接口返回可能是 excel 或 JSON(text)."""
            # 1) excel
            df = _try_parse_excel(content)
            if df is not None and not df.empty:
                code_col = None
                name_col = None
                for c in df.columns:
                    c_str = str(c)
                    if code_col is None and any(k in c_str for k in ["A股代码", "证券代码", "股票代码", "代码"]):
                        code_col = c
                    if name_col is None and any(k in c_str for k in ["证券简称", "股票简称", "简称", "名称"]):
                        name_col = c

                if code_col is not None:
                    parsed: List[Dict[str, Any]] = []
                    for _, row in df.iterrows():
                        raw_code = str(row.get(code_col, "") or "").strip()
                        if raw_code.isdigit():
                            raw_name = (
                                str(row.get(name_col, "") or raw_code).strip()
                                if name_col is not None
                                else raw_code
                            )
                            parsed.append({"code": raw_code, "name": raw_name})
                    return parsed

            # 2) json/text
            try:
                text = content.decode("utf-8", errors="ignore")
            except Exception:
                text = ""

            import json

            try:
                obj = json.loads(text)
                data = obj.get("result", {}).get("data", [])
                parsed2: List[Dict[str, Any]] = []
                if isinstance(data, list):
                    for row in data:
                        if not isinstance(row, dict):
                            continue
                        code = str(row.get("A_STOCK_CODE") or row.get("SECURITY_CODE") or "").strip()
                        name = str(row.get("A_STOCK_ABBR") or row.get("SECURITY_ABBR") or code).strip()
                        if code.isdigit():
                            parsed2.append({"code": code, "name": name or code})
                if parsed2:
                    return parsed2
            except Exception:
                pass

            # 3) last resort: regex
            import re

            codes = sorted(set(re.findall(r"\b\d{6}\b", text)))
            return [{"code": c, "name": c} for c in codes]

        # 1) SSE main/star
        for url, suffix in [(sse_main_url, ".SH"), (sse_star_url, ".SH")]:
            if not url:
                continue
            try:
                headers = {"Referer": "https://www.sse.com.cn/"}
                resp = self._session.get(url, headers=headers, timeout=60)
                resp.raise_for_status()

                parsed = _parse_sse_response(resp.content)
                for row in parsed:
                    code = str(row.get("code") or "").strip()
                    name = str(row.get("name") or code).strip()
                    if code.isdigit():
                        _append(f"{code}{suffix}", name)
            except Exception as e:
                logger.warning(f"SSE universe fetch failed: {e}")

        # 2) SZSE: sometimes returns 403 without proper headers; keep it optional.
        if szse_url:
            try:
                import io

                headers = {"User-Agent": "Mozilla/5.0", "Accept": "*/*", "Referer": "https://www.szse.cn/"}
                resp = self._session.get(szse_url, headers=headers, timeout=60)
                resp.raise_for_status()
                df = pd.read_excel(io.BytesIO(resp.content))

                code_col = None
                name_col = None
                for c in df.columns:
                    c_str = str(c)
                    if code_col is None and any(k in c_str for k in ["证券代码", "A股代码", "股票代码", "代码"]):
                        code_col = c
                    if name_col is None and any(k in c_str for k in ["证券简称", "A股简称", "股票简称", "简称", "名称"]):
                        name_col = c

                if code_col is not None:
                    for _, row in df.iterrows():
                        raw_code = str(row.get(code_col, "") or "").strip()
                        if not raw_code or not raw_code.isdigit():
                            continue
                        symbol = f"{raw_code}.SZ"
                        raw_name = (
                            str(row.get(name_col, "") or raw_code).strip()
                            if name_col is not None
                            else raw_code
                        )
                        _append(symbol, raw_name)
            except Exception as e:
                logger.warning(f"SZSE universe fetch failed (optional): {e}")

        dedup: Dict[str, Dict[str, Any]] = {}
        for it in items:
            sym = str(it.get("symbol") or "")
            if sym and sym not in dedup:
                dedup[sym] = it

        return list(dedup.values())

    def _get_hkconnect_universe_symbols(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """获取港股通标的清单（上交所披露接口，可能返回 xls/json）"""
        if self._session is None:
            return []

        from app.core.config import global_config

        api_cfg = global_config.get("api", {}) or {}
        hk_url = str(api_cfg.get("hkconnect_stocks", "") or "")
        if not hk_url:
            return []

        def _try_parse_excel(content: bytes) -> Optional[pd.DataFrame]:
            import io

            try:
                return pd.read_excel(io.BytesIO(content))
            except Exception:
                return None

        try:
            headers = {"Referer": "https://www.sse.com.cn/"}
            resp = self._session.get(hk_url, headers=headers, timeout=60)
            resp.raise_for_status()

            df = _try_parse_excel(resp.content)
            if df is not None and not df.empty:
                code_col = None
                name_col = None
                for c in df.columns:
                    c_str = str(c)
                    if code_col is None and any(k in c_str for k in ["证券代码", "股票代码", "代码"]):
                        code_col = c
                    if name_col is None and any(k in c_str for k in ["中文简称", "中文简称(参考)", "证券简称", "简称", "名称"]):
                        name_col = c

                if code_col is None:
                    return []

                items: List[Dict[str, Any]] = []
                for _, row in df.iterrows():
                    raw_code = str(row.get(code_col, "") or "").strip()
                    if not raw_code:
                        continue

                    code_digits = "".join([ch for ch in raw_code if ch.isdigit()])
                    if not code_digits:
                        continue

                    code_5 = code_digits.zfill(5)
                    symbol = f"{code_5}.HK"
                    raw_name = (
                        str(row.get(name_col, "") or code_5).strip()
                        if name_col is not None
                        else code_5
                    )
                    items.append({"symbol": symbol, "name": raw_name})

                # Deduplicate
                dedup: Dict[str, Dict[str, Any]] = {}
                for it in items:
                    sym = str(it.get("symbol") or "")
                    if sym and sym not in dedup:
                        dedup[sym] = it
                return list(dedup.values())

            # 2) json/text fallback
            text = resp.content.decode("utf-8", errors="ignore")
            import json

            try:
                obj = json.loads(text)
                data = obj.get("result", {}).get("data", [])
                if not isinstance(data, list):
                    data = []
                items2: List[Dict[str, Any]] = []
                for row in data:
                    if not isinstance(row, dict):
                        continue
                    code = str(row.get("HGT_STK_CODE") or row.get("STK_CODE") or "").strip()
                    name = str(row.get("HGT_STK_NAME") or row.get("STK_NAME") or code).strip()
                    code_digits = "".join([ch for ch in code if ch.isdigit()])
                    if not code_digits:
                        continue
                    symbol = f"{code_digits.zfill(5)}.HK"
                    items2.append({"symbol": symbol, "name": name or symbol})
                if items2:
                    return items2
            except Exception:
                pass

            import re

            codes = sorted(set(re.findall(r"\b\d{5}\b", text)))
            return [{"symbol": f"{c}.HK", "name": c} for c in codes]

        except Exception as e:
            logger.warning(f"HKCONNECT universe fetch failed: {e}")
            return []