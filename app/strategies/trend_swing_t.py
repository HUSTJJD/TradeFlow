from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import pandas as pd

import logging

from app.core.config import global_config
from app.core.constants import SignalType
from app.strategies.base import Strategy
from app.utils.indicators import (
    calculate_adx,
    calculate_atr,
    calculate_donchian_channel,
    calculate_ema,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TrendSwingConfig:
    """偏波段的趋势突破策略参数。

    说明：默认值仅作为兜底，建议在 `config/config.yaml` 的
    `strategy.params` 下配置，便于回测与实盘保持一致。
    """

    ema_fast: int = 20
    ema_slow: int = 60
    adx_period: int = 14
    adx_threshold: float = 20.0

    donchian_period: int = 20

    atr_period: int = 14
    atr_stop_loss: float = 2.5
    atr_trailing: float = 3.0

    take_profit_r_multiple_1: float = 2.0
    take_profit_ratio_1: float = 0.5

    enable_t: bool = True
    t_rsi_period: int = 6
    t_overbought: float = 75.0
    t_oversold: float = 25.0

    t_step_ratio: float = 0.10

    base_target_position_ratio: float = 0.20


def _calculate_rsi_fast(df: pd.DataFrame, period: int, column: str = "close") -> pd.Series:
    delta = df[column].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return pd.Series(rsi, index=df.index, dtype="float64")


class TrendSwingTStrategy(Strategy):
    """趋势突破 + ATR 风控 + 目标仓位管理 + 低频做T（可选）。"""

    def __init__(
        self,
        config: Optional[TrendSwingConfig] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name="TrendSwingT", description="趋势突破 + ATR风控 + 目标仓位管理 + 低频做T策略")

        # 兼容工厂方法：get_strategy(name, **strategy.params)
        # - 若显式传入 config，则优先使用
        # - 否则把 kwargs 视为参数覆盖，并且也允许从 YAML 读取默认值
        params = global_config.get("strategy.params", {}) or {}
        merged = {**params, **kwargs}

        if config is None:
            config = TrendSwingConfig(
                **{k: v for k, v in merged.items() if k in TrendSwingConfig.__annotations__}
            )
        self.cfg = config

        self._entry_price: Dict[str, float] = {}
        self._trail_high: Dict[str, float] = {}
        self._t_last_date: Dict[str, str] = {}
        self._t_count: Dict[str, int] = {}
        self._tp1_done: Dict[str, bool] = {}
        self._base_target_ratio: Dict[str, float] = {}

        self._min_data_length = max(
            self.cfg.ema_slow,
            self.cfg.donchian_period,
            self.cfg.atr_period,
            self.cfg.adx_period,
        ) + 5

    def _on_initialize(self, **kwargs: Any) -> bool:
        """趋势摆动策略初始化"""
        # 验证参数有效性
        if self.cfg.ema_fast <= 0 or self.cfg.ema_slow <= 0:
            raise ValueError("EMA周期必须为正整数")
        if self.cfg.ema_fast >= self.cfg.ema_slow:
            raise ValueError("快速EMA周期必须小于慢速EMA周期")
        if self.cfg.adx_threshold <= 0:
            raise ValueError("ADX阈值必须为正数")
        if self.cfg.atr_stop_loss <= 0 or self.cfg.atr_trailing <= 0:
            raise ValueError("ATR止损倍数必须为正数")
        if self.cfg.base_target_position_ratio <= 0 or self.cfg.base_target_position_ratio > 1:
            raise ValueError("基础目标仓位比例必须在(0, 1]范围内")
        
        return True

    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """分析市场数据并生成交易信号"""
        # 数据验证
        if not self.validate_data(df, ['open', 'high', 'low', 'close']):
            return {"action": SignalType.HOLD, "reason": "数据无效"}

        if len(df) < self._min_data_length:
            return {"action": SignalType.HOLD, "reason": "数据不足"}

        df = df.sort_index()

        # 计算技术指标
        df = calculate_ema(df, self.cfg.ema_fast, out_col="ema_fast")
        df = calculate_ema(df, self.cfg.ema_slow, out_col="ema_slow")
        df = calculate_adx(df, self.cfg.adx_period)
        df = calculate_atr(df, self.cfg.atr_period)
        df = calculate_donchian_channel(df, self.cfg.donchian_period)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        close = float(last["close"])
        atr = float(last["atr"]) if pd.notna(last["atr"]) else 0.0
        ema_fast = float(last["ema_fast"])
        ema_slow = float(last["ema_slow"])
        adx = float(last["adx"]) if pd.notna(last["adx"]) else 0.0

        prev_don_high = float(prev["donchian_high"])

        has_pos = self._entry_price.get(symbol) is not None and self._entry_price.get(symbol, 0.0) > 0

        trend_up = (ema_fast > ema_slow) and (adx >= self.cfg.adx_threshold)

        # 1) 持仓：止损/追踪止损/趋势破坏
        if has_pos:
            entry_price = float(self._entry_price[symbol])
            self._trail_high[symbol] = max(self._trail_high.get(symbol, close), close)
            trail_high = float(self._trail_high[symbol])

            r = atr if atr > 0 else max(entry_price * 0.02, 0.01)
            stop_loss = entry_price - self.cfg.atr_stop_loss * r
            trailing_stop = trail_high - self.cfg.atr_trailing * r
            hard_stop = max(stop_loss, trailing_stop)

            if close <= hard_stop or (ema_fast < ema_slow):
                self._reset_symbol(symbol)
                return {
                    "action": SignalType.SELL,
                    "price": close,
                    "reason": f"退出: {'止损/追踪止损' if close <= hard_stop else '趋势破坏'} (close={close:.2f}, stop={hard_stop:.2f})",
                    "trade_tag": "SWING",
                    "target_position_ratio": 0.0,
                    "factors": {
                        "close": close,
                        "entry": entry_price,
                        "atr": atr,
                        "stop": float(hard_stop),
                        "ema_fast": ema_fast,
                        "ema_slow": ema_slow,
                        "adx": adx,
                    },
                }

            # 2) 分批止盈：把目标仓位降到 50%
            tp1_done = self._tp1_done.get(symbol, False)
            tp1_price = entry_price + self.cfg.take_profit_r_multiple_1 * r
            if (not tp1_done) and close >= tp1_price:
                self._tp1_done[symbol] = True
                base_ratio = float(self._base_target_ratio.get(symbol, self.cfg.base_target_position_ratio))
                return {
                    "action": SignalType.SELL,
                    "price": close,
                    "reason": f"分批止盈: 达到 {self.cfg.take_profit_r_multiple_1:.1f}R (tp={tp1_price:.2f})",
                    "trade_tag": "SWING",
                    "target_position_ratio": base_ratio * float(self.cfg.take_profit_ratio_1),
                    "factors": {
                        "close": close,
                        "entry": entry_price,
                        "atr": atr,
                        "tp1": float(tp1_price),
                    },
                }

            # 3) 做T：低频目标仓位再平衡
            if self.cfg.enable_t:
                date_str = str(df.index[-1]).split(" ")[0]
                if self._t_last_date.get(symbol) != date_str:
                    self._t_last_date[symbol] = date_str
                    self._t_count[symbol] = 0

                t_count = self._t_count.get(symbol, 0)
                if t_count < 2:
                    rsi_fast = float(_calculate_rsi_fast(df, self.cfg.t_rsi_period).iloc[-1])
                    deviation = (close / ema_fast - 1.0) if ema_fast > 0 else 0.0

                    base_ratio = float(self._base_target_ratio.get(symbol, self.cfg.base_target_position_ratio))

                    # 超买：轻减仓
                    if rsi_fast >= self.cfg.t_overbought and deviation > 0.01:
                        self._t_count[symbol] = t_count + 1
                        return {
                            "action": SignalType.SELL,
                            "price": close,
                            "reason": f"做T减仓: RSI{self.cfg.t_rsi_period}={rsi_fast:.1f} 超买",
                            "trade_tag": "T",
                            "target_position_ratio": max(0.0, base_ratio * (1.0 - self.cfg.t_step_ratio)),
                            "factors": {"rsi_fast": rsi_fast, "deviation": deviation, "close": close, "atr": atr},
                        }

                    # 超卖：轻加仓（依然由仓位管理器计算数量与现金约束）
                    if rsi_fast <= self.cfg.t_oversold and deviation < -0.01:
                        self._t_count[symbol] = t_count + 1
                        return {
                            "action": SignalType.BUY,
                            "price": close,
                            "reason": f"做T加仓: RSI{self.cfg.t_rsi_period}={rsi_fast:.1f} 超卖",
                            "trade_tag": "T",
                            "target_position_ratio": base_ratio * (1.0 + self.cfg.t_step_ratio),
                            "factors": {"rsi_fast": rsi_fast, "deviation": deviation, "close": close, "atr": atr},
                        }

        # 4) 入场：趋势过滤 + 突破
        breakout = close > prev_don_high
        if (not has_pos) and trend_up and breakout:
            self._entry_price[symbol] = close
            self._trail_high[symbol] = close
            self._tp1_done[symbol] = False

            self._base_target_ratio[symbol] = float(self.cfg.base_target_position_ratio)

            return {
                "action": SignalType.BUY,
                "price": close,
                "reason": f"趋势突破入场: close突破Donchian({self.cfg.donchian_period})上轨",
                "trade_tag": "SWING",
                "target_position_ratio": self._base_target_ratio[symbol],
                "factors": {
                    "close": close,
                    "atr": atr,
                    "ema_fast": ema_fast,
                    "ema_slow": ema_slow,
                    "adx": adx,
                    "donchian_prev_high": float(prev_don_high),
                },
            }

        return {
            "action": SignalType.HOLD,
            "reason": "无信号",
            "factors": {
                "close": close,
                "ema_fast": ema_fast,
                "ema_slow": ema_slow,
                "adx": adx,
                "trend_up": trend_up,
            },
        }

    def _reset_symbol(self, symbol: str) -> None:
        """重置指定标的的状态"""
        self._entry_price.pop(symbol, None)
        self._trail_high.pop(symbol, None)
        self._tp1_done.pop(symbol, None)
        self._base_target_ratio.pop(symbol, None)

        self._t_last_date.pop(symbol, None)
        self._t_count.pop(symbol, None)

    def get_info(self) -> Dict[str, Any]:
        """获取趋势摆动策略的详细信息"""
        base_info = super().get_info()
        base_info.update({
            "parameters": {
                "ema_fast": self.cfg.ema_fast,
                "ema_slow": self.cfg.ema_slow,
                "adx_period": self.cfg.adx_period,
                "adx_threshold": self.cfg.adx_threshold,
                "donchian_period": self.cfg.donchian_period,
                "atr_period": self.cfg.atr_period,
                "atr_stop_loss": self.cfg.atr_stop_loss,
                "atr_trailing": self.cfg.atr_trailing,
                "take_profit_r_multiple_1": self.cfg.take_profit_r_multiple_1,
                "take_profit_ratio_1": self.cfg.take_profit_ratio_1,
                "enable_t": self.cfg.enable_t,
                "t_rsi_period": self.cfg.t_rsi_period,
                "t_overbought": self.cfg.t_overbought,
                "t_oversold": self.cfg.t_oversold,
                "t_step_ratio": self.cfg.t_step_ratio,
                "base_target_position_ratio": self.cfg.base_target_position_ratio,
                "min_data_length": self._min_data_length
            }
        })
        return base_info

    def _on_cleanup(self) -> None:
        """清理策略资源"""
        self._entry_price.clear()
        self._trail_high.clear()
        self._t_last_date.clear()
        self._t_count.clear()
        self._tp1_done.clear()
        self._base_target_ratio.clear()
        logger.info("趋势摆动策略资源已清理")
