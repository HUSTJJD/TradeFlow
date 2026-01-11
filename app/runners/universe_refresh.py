from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from longport.openapi import QuoteContext, Period

from app.core.config import global_config
from app.data.provider import (
    fetch_history_candles,
    get_stock_names,
    refresh_universe_cache,
    save_cn_universe_symbols,
    save_hkconnect_universe_symbols,
    load_cn_universe_symbols,
    load_hkconnect_universe_symbols,
)

logger = logging.getLogger(__name__)


def _try_import_akshare():
    try:
        import akshare as ak  # type: ignore

        return ak
    except Exception:
        return None


def _cn_symbol_to_longport(code: str) -> Optional[str]:
    code = (code or "").strip()
    if len(code) != 6 or not code.isdigit():
        return None

    # 简化规则：6xxxx -> SH，其余 -> SZ（对沪深主板/创业板/中小板均基本可用）
    if code.startswith("6"):
        return f"{code}.SH"
    return f"{code}.SZ"


def _load_cn_universe_by_akshare() -> List[Dict[str, Any]]:
    """从 AkShare 拉取 A 股全量标的（代码、名称、行业、部分财务指标）。

    返回 dict 列表：
    - symbol: `600000.SH` / `000001.SZ`
    - name
    - industry
    - fundamentals: dict
    """

    ak = _try_import_akshare()
    if ak is None:
        logger.error("未安装 akshare，无法离线拉取 A 股全量标的。请先 pip install -r requirements.txt")
        return []

    base = ak.stock_info_a_code_name()
    if base is None or base.empty:
        return []

    results: List[Dict[str, Any]] = []

    # 这里会较慢：逐个拉行业信息。后续可以改为使用更批量的行业接口。
    for _, row in base.iterrows():
        code = str(row.get("code", "")).strip()
        name = str(row.get("name", "")).strip()
        symbol = _cn_symbol_to_longport(code)
        if not symbol:
            continue

        industry = "UNKNOWN"
        fundamentals: Dict[str, Any] = {}

        try:
            market_prefix = "sh" if code.startswith("6") else "sz"
            info = ak.stock_individual_info_em(symbol=f"{market_prefix}{code}")
            if info is not None and not info.empty:
                # info: columns [item, value]
                ind = info.loc[info["item"] == "所属行业", "value"]
                if len(ind) > 0:
                    industry = str(ind.values[0]).strip() or "UNKNOWN"
        except Exception:
            pass

        # 财务指标：拿最新一期（若失败就跳过）
        try:
            fin = ak.stock_financial_analysis_indicator(symbol=code)
            if fin is not None and not fin.empty:
                latest = fin.iloc[0].to_dict()
                fundamentals = {
                    "roe": latest.get("净资产收益率(%)"),
                    "gross_margin": latest.get("毛利率(%)"),
                    "debt_ratio": latest.get("资产负债率(%)"),
                }
        except Exception:
            pass

        results.append(
            {
                "symbol": symbol,
                "name": name,
                "industry": industry,
                "fundamentals": fundamentals,
            }
        )

    return results


def _load_hkconnect_universe_by_eastmoney() -> List[Dict[str, str]]:
    """通过东方财富接口拉取港股通标的清单（仅代码+名称）。

    说明：
    - 该接口是公开数据源，可能存在频控/字段变更风险
    - 我们尽量只依赖最稳定的字段：f12(代码)、f14(名称)

    返回：[{"symbol": "00700.HK", "name": "腾讯控股"}, ...]
    """

    url = "https://push2.eastmoney.com/api/qt/clist/get"

    # 经验参数：m:128+t:3 常被用作“港股通”列表过滤
    # 若后续发现覆盖不全，可在这里扩展 fs（例如叠加不同市场分类）
    fs = "m:128+t:3"

    params = {
        "po": "1",
        "pz": "5000",
        "pn": "1",
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fields": "f12,f14",
        "fs": fs,
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://quote.eastmoney.com/",
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        payload = resp.json() or {}
        data = (payload.get("data") or {})
        diff = data.get("diff") or []

        items: List[Dict[str, str]] = []
        for row in diff:
            if not isinstance(row, dict):
                continue
            code = str(row.get("f12") or "").strip()
            name = str(row.get("f14") or "").strip()
            if not code:
                continue
            # 港股通标的用 .HK 作为后缀，供后续长桥行情/历史K线查询
            symbol = f"{code}.HK"
            items.append({"symbol": symbol, "name": name or symbol})

        return items
    except Exception as e:
        logger.warning(f"东方财富拉取港股通标的清单失败: {e}")
        return []


def _calc_tech_score(df: pd.DataFrame) -> float:
    # ... existing code ...
    pass

def _calc_hot_score(df: pd.DataFrame) -> float:
# ... existing code ...
	pass

def _calc_news_score(_: str) -> float:
# ... existing code ...
	pass

def _calc_fundamental_score(fundamentals: Dict[str, Any]) -> float:
    """财务面打分（占位实现，先做一个偏‘质量’的简单分数）。"""

    if not fundamentals:
        return 0.0

    def _to_float(v) -> float:
        try:
            if v is None:
                return 0.0
            return float(v)
        except Exception:
            return 0.0

    roe = _to_float(fundamentals.get("roe"))
    gross_margin = _to_float(fundamentals.get("gross_margin"))
    debt_ratio = _to_float(fundamentals.get("debt_ratio"))

    # 偏好：ROE 高、毛利率高、负债率低
    return 0.8 * roe + 0.2 * gross_margin - 0.3 * debt_ratio


def run_universe_symbols_refresh() -> None:
    """第一步：仅拉取 A 股与港股通的“标的代码+名称”，并单独保存到本地。

    - A股：AkShare
    - 港股通：东方财富（push2 接口）

    注意：该步骤不依赖长桥 API。
    """

    cn_rows = _load_cn_universe_by_akshare()
    cn_items = [{"symbol": r["symbol"], "name": r.get("name", r["symbol"]) } for r in cn_rows]
    save_cn_universe_symbols(cn_items)
    logger.info(f"已保存 A股 标的清单: {len(cn_items)}")

    hkconnect_items = _load_hkconnect_universe_by_eastmoney()
    save_hkconnect_universe_symbols(hkconnect_items)
    logger.info(f"已保存 港股通 标的清单: {len(hkconnect_items)}")


def run_universe_refresh(quote_ctx: QuoteContext) -> None:
    """第二步：基于第一步保存的标的清单，用长桥 API 拉取详细数据并打分。"""

    cfg = global_config.get("universe.refresh", {}) or {}
    markets = cfg.get("markets", ["CN", "HKCONNECT"]) or ["CN", "HKCONNECT"]
    lookback_days = int(cfg.get("lookback_days", 120))

    end_date = date.today()
    start_date = end_date - timedelta(days=lookback_days * 2)

    universe_items: List[Dict[str, Any]] = []

    if any((m or "").upper() == "CN" for m in markets):
        universe_items.extend(load_cn_universe_symbols())

    if any((m or "").upper() == "HKCONNECT" for m in markets):
        universe_items.extend(load_hkconnect_universe_symbols())

    if not universe_items:
        logger.error("标的清单为空：请先运行第一步 run_universe_symbols_refresh() 生成标的代码+名称清单")
        refresh_universe_cache(snapshot={"symbols": []}, scores={"candidates": []})
        return

    all_symbols = sorted(list({r.get("symbol") for r in universe_items if r.get("symbol")}))

    logger.info(f"标的清单数量: {len(all_symbols)}")

    # 名称映射：优先使用第一步保存的 name，再用长桥补齐
    name_map: Dict[str, str] = {r["symbol"]: r.get("name", r["symbol"]) for r in universe_items if r.get("symbol")}

    try:
        batch_size = 200
        for i in range(0, len(all_symbols), batch_size):
            batch = all_symbols[i : i + batch_size]
            name_map.update(get_stock_names(quote_ctx, batch))
    except Exception:
        pass

    # 第二步暂不强依赖行业/财务：这些在第一步（或第三方）里补齐后会更准
    industry_map: Dict[str, str] = {r["symbol"]: (r.get("industry") or "UNKNOWN") for r in universe_items if r.get("symbol")}
    fundamental_map: Dict[str, Dict[str, Any]] = {
        r["symbol"]: (r.get("fundamentals") or {}) for r in universe_items if r.get("symbol")
    }

    candidates: List[Dict[str, Any]] = []

    for idx, symbol in enumerate(all_symbols):
        if idx % 200 == 0:
            logger.info(f"进度: {idx}/{len(all_symbols)}")

        try:
            df = fetch_history_candles(
                quote_ctx,
                symbol,
                Period.Day,
                start_date,
                end_date,
                warmup_days=0,
            )
            if df.empty:
                continue

            tech = _calc_tech_score(df)
            hot = _calc_hot_score(df)
            news = _calc_news_score(symbol)
            fundamental = _calc_fundamental_score(fundamental_map.get(symbol, {}))

            industry = industry_map.get(symbol, "UNKNOWN")
            score = 0.6 * tech + 0.15 * hot + 0.05 * news + 0.2 * fundamental

            candidates.append(
                {
                    "symbol": symbol,
                    "name": name_map.get(symbol, symbol),
                    "industry": industry,
                    "score": float(score),
                    "components": {
                        "tech": float(tech),
                        "hot": float(hot),
                        "news": float(news),
                        "fundamental": float(fundamental),
                    },
                }
            )
        except Exception as e:
            logger.debug(f"跳过 {symbol}: {e}")

    candidates = sorted(candidates, key=lambda x: float(x.get("score", 0)), reverse=True)

    snapshot = {
        "as_of": str(end_date),
        "markets": markets,
        "symbols": all_symbols,
        "names": name_map,
        "industry": industry_map,
    }

    scores = {
        "as_of": str(end_date),
        "candidates": candidates,
    }

    refresh_universe_cache(snapshot=snapshot, scores=scores)

    logger.info(f"刷新完成：候选={len(candidates)}，已写入本地缓存")
