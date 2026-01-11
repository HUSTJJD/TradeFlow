from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Protocol, cast

import pandas as pd
from longport.openapi import Period, QuoteContext

from app.core.config import global_config
from app.data.interface import ExchangeDataProvider
from app.data.provider import (
    fetch_history_candles,
    get_stock_names,
    refresh_universe_cache,
    save_cn_universe_symbols,
    save_hkconnect_universe_symbols,
)

logger = logging.getLogger(__name__)


class UniverseSymbolProvider(Protocol):
    def get_universe_symbols(self, market: str) -> List[Dict[str, Any]]:
        ...


class ExchangeUniverseSymbolProvider:
    def __init__(self) -> None:
        self._provider = ExchangeDataProvider()

    def get_universe_symbols(self, market: str) -> List[Dict[str, Any]]:
        return self._provider.get_universe_symbols(market)


class UniverseScorer(Protocol):
    def score(self, symbol: str, candles: pd.DataFrame, fundamentals: Dict[str, Any]) -> float:
        ...


class TechnicalMomentumScorer:
    """Simple momentum score by 5-day price change."""

    def score(self, symbol: str, candles: pd.DataFrame, fundamentals: Dict[str, Any]) -> float:
        if candles.empty or len(candles) < 5:
            return 0.0

        recent_close = candles["close"].iloc[-5:].values
        if len(recent_close) < 2:
            return 0.0

        price_change = (recent_close[-1] - recent_close[0]) / recent_close[0]
        return float(price_change * 100)


class VolatilityHotnessScorer:
    """Simple hotness score by 20-day volatility."""

    def score(self, symbol: str, candles: pd.DataFrame, fundamentals: Dict[str, Any]) -> float:
        if candles.empty or len(candles) < 20:
            return 0.0

        recent_volatility = candles["close"].iloc[-20:].pct_change().std()
        return float(recent_volatility * 100)


class PlaceholderNewsScorer:
    def score(self, symbol: str, candles: pd.DataFrame, fundamentals: Dict[str, Any]) -> float:
        return 0.0


class FundamentalQualityScorer:
    def score(self, symbol: str, candles: pd.DataFrame, fundamentals: Dict[str, Any]) -> float:
        if not fundamentals:
            return 0.0

        roe = self._to_float(fundamentals.get("roe"))
        gross_margin = self._to_float(fundamentals.get("gross_margin"))
        debt_ratio = self._to_float(fundamentals.get("debt_ratio"))

        return 0.8 * roe + 0.2 * gross_margin - 0.3 * debt_ratio

    @staticmethod
    def _to_float(value: Any) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except Exception:
            return 0.0


@dataclass(frozen=True)
class UniverseScoringWeights:
    technical: float
    sentiment: float
    news: float
    fundamental: float

    @classmethod
    def from_config(cls) -> "UniverseScoringWeights":
        scoring_cfg = global_config.get("data.scoring", {}) or {}
        return cls(
            technical=float(scoring_cfg.get("technical", 0.6)),
            sentiment=float(scoring_cfg.get("sentiment", 0.15)),
            news=float(scoring_cfg.get("news", 0.05)),
            fundamental=float(scoring_cfg.get("fundamental", 0.2)),
        )


class UniverseCompositeScorer:
    def __init__(
        self,
        weights: UniverseScoringWeights,
        technical: UniverseScorer,
        sentiment: UniverseScorer,
        news: UniverseScorer,
        fundamental: UniverseScorer,
    ) -> None:
        self._weights = weights
        self._technical = technical
        self._sentiment = sentiment
        self._news = news
        self._fundamental = fundamental

    def score(self, symbol: str, candles: pd.DataFrame, fundamentals: Dict[str, Any]) -> Dict[str, float]:
        tech = float(self._technical.score(symbol, candles, fundamentals))
        hot = float(self._sentiment.score(symbol, candles, fundamentals))
        news = float(self._news.score(symbol, candles, fundamentals))
        fundamental = float(self._fundamental.score(symbol, candles, fundamentals))

        total = (
            self._weights.technical * tech
            + self._weights.sentiment * hot
            + self._weights.news * news
            + self._weights.fundamental * fundamental
        )

        return {
            "score": float(total),
            "tech": tech,
            "hot": hot,
            "news": news,
            "fundamental": fundamental,
        }


class UniverseCandidateSelector:
    def __init__(self, max_symbols: int, one_per_industry: bool) -> None:
        self._max_symbols = int(max_symbols)
        self._one_per_industry = bool(one_per_industry)

    def select(self, candidates: List[Dict[str, Any]]) -> List[str]:
        selected: List[str] = []
        used_industries: set[str] = set()

        for item in sorted(candidates, key=lambda x: float(x.get("score", 0.0)), reverse=True):
            symbol = cast(str, item.get("symbol") or "")
            if not symbol:
                continue

            industry = cast(str, item.get("industry") or "UNKNOWN")
            if self._one_per_industry and industry in used_industries:
                continue

            selected.append(symbol)
            used_industries.add(industry)

            if len(selected) >= self._max_symbols:
                break

        return selected


class UniverseRefreshService:
    def __init__(self, symbol_provider: UniverseSymbolProvider) -> None:
        self._symbol_provider = symbol_provider

    def refresh_symbols(self, markets: List[str]) -> List[Dict[str, Any]]:
        all_items: List[Dict[str, Any]] = []

        if any((m or "").upper() == "CN" for m in markets):
            cn_items = self._symbol_provider.get_universe_symbols("CN")
            if cn_items:
                save_cn_universe_symbols(cn_items)
                all_items.extend(cn_items)
                logger.info(f"CN universe symbols saved: {len(cn_items)}")
            else:
                logger.warning("Failed to load CN universe symbols")

        if any((m or "").upper() == "HKCONNECT" for m in markets):
            hk_items = self._symbol_provider.get_universe_symbols("HKCONNECT")
            if hk_items:
                save_hkconnect_universe_symbols(hk_items)
                all_items.extend(hk_items)
                logger.info(f"HKCONNECT universe symbols saved: {len(hk_items)}")
            else:
                logger.warning("Failed to load HKCONNECT universe symbols")

        if not all_items:
            logger.error("Universe symbol refresh failed: no markets returned data")
        else:
            logger.info(f"Universe symbols refreshed: total={len(all_items)}")

        return all_items


class UniverseScoringService:
    def __init__(self, composite_scorer: UniverseCompositeScorer) -> None:
        self._composite_scorer = composite_scorer

    def build_candidates(
        self,
        quote_ctx: QuoteContext,
        symbols: List[str],
        name_map: Dict[str, str],
        industry_map: Dict[str, str],
        board_map: Dict[str, str],
        fundamentals_map: Dict[str, Dict[str, Any]],
        lookback_days: int,
        batch_size: int,
    ) -> List[Dict[str, Any]]:
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days * 2)

        try:
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i : i + batch_size]
                name_map.update(get_stock_names(quote_ctx, batch))
        except Exception:
            pass

        candidates: List[Dict[str, Any]] = []

        for idx, symbol in enumerate(symbols):
            if idx % 200 == 0:
                logger.info(f"Progress: {idx}/{len(symbols)}")

            try:
                df = fetch_history_candles(
                    quote_ctx,
                    symbol,
                    cast(Period, Period.Day),
                    start_date,
                    end_date,
                    warmup_days=0,
                )
                if df.empty:
                    continue

                score_components = self._composite_scorer.score(
                    symbol, df, fundamentals_map.get(symbol, {})
                )

                candidates.append(
                    {
                        "symbol": symbol,
                        "name": name_map.get(symbol, symbol),
                        "industry": industry_map.get(symbol, "UNKNOWN"),
                        "board": board_map.get(symbol, "UNKNOWN"),
                        "score": float(score_components["score"]),
                        "components": {
                            "tech": float(score_components["tech"]),
                            "hot": float(score_components["hot"]),
                            "news": float(score_components["news"]),
                            "fundamental": float(score_components["fundamental"]),
                        },
                    }
                )
            except Exception as e:
                logger.debug(f"Skip {symbol}: {e}")

        candidates.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
        return candidates


def run_universe_symbols_refresh() -> None:
    """Step 1: refresh universe symbol list without relying on Longbridge API."""

    cfg = global_config.get("universe.refresh", {}) or {}
    markets = cast(List[str], cfg.get("markets", ["CN", "HKCONNECT"]) or ["CN", "HKCONNECT"])

    service = UniverseRefreshService(symbol_provider=ExchangeUniverseSymbolProvider())
    service.refresh_symbols(markets)


def run_universe_refresh(quote_ctx: QuoteContext) -> None:
    """Step 2: load universe list, fetch data from Longbridge, and score candidates."""

    cfg = global_config.get("universe.refresh", {}) or {}
    markets = cast(List[str], cfg.get("markets", ["CN", "HKCONNECT"]) or ["CN", "HKCONNECT"])
    lookback_days = int(cfg.get("lookback_days", 120))

    data_cfg = global_config.get("data", {}) or {}
    batch_size = int(data_cfg.get("batch_size", 200))

    symbol_provider = ExchangeUniverseSymbolProvider()

    universe_items: List[Dict[str, Any]] = []
    if any((m or "").upper() == "CN" for m in markets):
        universe_items.extend(symbol_provider.get_universe_symbols("CN"))
    if any((m or "").upper() == "HKCONNECT" for m in markets):
        universe_items.extend(symbol_provider.get_universe_symbols("HKCONNECT"))

    if not universe_items:
        logger.error(
            "Universe symbol list is empty. Run run_universe_symbols_refresh() first to generate it."
        )
        refresh_universe_cache(snapshot={"symbols": []}, scores={"candidates": []})
        return

    all_symbols = sorted({cast(str, r["symbol"]) for r in universe_items if r.get("symbol")})
    logger.info(f"Universe symbols: {len(all_symbols)}")

    name_map: Dict[str, str] = {
        r["symbol"]: cast(str, r.get("name", r["symbol"]))
        for r in universe_items
        if r.get("symbol")
    }
    board_map: Dict[str, str] = {
        r["symbol"]: cast(str, r.get("board", "UNKNOWN"))
        for r in universe_items
        if r.get("symbol")
    }

    industry_map: Dict[str, str] = {
        r["symbol"]: cast(str, (r.get("industry") or "UNKNOWN"))
        for r in universe_items
        if r.get("symbol")
    }
    fundamentals_map: Dict[str, Dict[str, Any]] = {
        r["symbol"]: cast(Dict[str, Any], (r.get("fundamentals") or {}))
        for r in universe_items
        if r.get("symbol")
    }

    weights = UniverseScoringWeights.from_config()
    composite = UniverseCompositeScorer(
        weights=weights,
        technical=TechnicalMomentumScorer(),
        sentiment=VolatilityHotnessScorer(),
        news=PlaceholderNewsScorer(),
        fundamental=FundamentalQualityScorer(),
    )

    scoring_service = UniverseScoringService(composite_scorer=composite)
    candidates = scoring_service.build_candidates(
        quote_ctx=quote_ctx,
        symbols=all_symbols,
        name_map=name_map,
        industry_map=industry_map,
        board_map=board_map,
        fundamentals_map=fundamentals_map,
        lookback_days=lookback_days,
        batch_size=batch_size,
    )

    end_date = date.today()
    snapshot = {
        "as_of": str(end_date),
        "markets": markets,
        "symbols": all_symbols,
        "names": name_map,
        "industry": industry_map,
        "board": board_map,
    }

    scores = {
        "as_of": str(end_date),
        "candidates": candidates,
    }

    refresh_universe_cache(snapshot=snapshot, scores=scores)

    logger.info(f"Universe refresh completed: candidates={len(candidates)}")
