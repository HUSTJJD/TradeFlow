import logging
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Any, Dict, List, Optional, Tuple, cast
import os
from datetime import datetime

from app.core.constants import SignalType

logger = logging.getLogger(__name__)


def create_performance_chart(
    equity_curve: List[Dict[str, Any]],
    trades: List[Dict[str, Any]],
    benchmark_data: Dict[str, pd.DataFrame],
    config: Dict[str, Any],
    output_dir: str = "reports",
    filename: str = "performance.html",
) -> str:
    """
    创建账户收益率与基准对比的交互式图表。

    Args:
        equity_curve: 账户权益曲线列表，每项包含 'time' 和 'equity'。
        trades: 交易记录列表。
        benchmark_data: 基准数据字典，键为 symbol，值为包含 'close' 的 DataFrame。
        config: 绘图配置字典。
        output_dir: 输出目录。
        filename: 输出文件名。

    Returns:
        生成的 HTML 文件路径。
    """
    if not equity_curve:
        logger.warning("没有权益数据，无法绘图")
        return ""

    df_account = pd.DataFrame(equity_curve)
    df_account["time"] = pd.to_datetime(df_account["time"])
    df_account.set_index("time", inplace=True)

    initial_equity = df_account.iloc[0]["equity"]
    df_account["return"] = (df_account["equity"] - initial_equity) / initial_equity

    df_account["cummax"] = df_account["equity"].cummax()
    df_account["drawdown"] = (df_account["equity"] - df_account["cummax"]) / df_account[
        "cummax"
    ]
    max_drawdown_val = df_account["drawdown"].min()

    mdd_start_date = None
    mdd_end_date = None
    mdd_start_return = 0
    mdd_end_return = 0

    if max_drawdown_val < 0:
        mdd_end_date = df_account["drawdown"].idxmin()
        mdd_start_date = df_account.loc[:mdd_end_date, "equity"].idxmax()

        mdd_start_return = df_account.loc[mdd_start_date, "return"]
        mdd_end_return = df_account.loc[mdd_end_date, "return"]

    fig = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.72, 0.28],
        specs=[[{"type": "xy"}, {"type": "table"}]],
        horizontal_spacing=0.06,
    )

    account_color = config.get("colors", {}).get("account", "#1f77b4")
    fig.add_trace(
        go.Scatter(
            x=df_account.index,
            y=df_account["return"],
            mode="lines",
            name="账户收益率",
            line=dict(color=account_color, width=2),
            hovertemplate="时间: %{x}<br>收益率: %{y:.2%}<br>权益: %{customdata:.2f}",
            customdata=df_account["equity"],
        ),
        row=1,
        col=1,
    )

    benchmarks_config = config.get("benchmarks", [])

    if not benchmarks_config and benchmark_data:
        for symbol in benchmark_data.keys():
            benchmarks_config.append({"symbol": symbol, "name": symbol})

    for bench_cfg in benchmarks_config:
        symbol = bench_cfg.get("symbol")
        if symbol not in benchmark_data:
            continue

        df_bench = benchmark_data[symbol]
        if df_bench.empty:
            continue

        start_time = df_account.index[0]
        end_time = df_account.index[-1]

        if not isinstance(df_bench.index, pd.DatetimeIndex):
            df_bench.index = pd.to_datetime(df_bench.index)

        mask = (df_bench.index >= start_time) & (df_bench.index <= end_time)
        df_bench_clipped = df_bench.loc[mask].copy()

        if df_bench_clipped.empty:
            continue

        initial_close = df_bench_clipped.iloc[0]["close"]
        df_bench_clipped["return"] = (
            df_bench_clipped["close"] - initial_close
        ) / initial_close

        color = bench_cfg.get("color", None)
        name = bench_cfg.get("name", symbol)

        fig.add_trace(
            go.Scatter(
                x=df_bench_clipped.index,
                y=df_bench_clipped["return"],
                mode="lines",
                name=name,
                line=dict(color=color, width=1.5, dash="dot"),
                hovertemplate=f"{name}<br>时间: %{{x}}<br>收益率: %{{y:.2%}}",
            ),
            row=1,
            col=1,
        )

    colors = config.get("colors", {})
    buy_color = colors.get("buy", "#2ca02c")
    sell_color = colors.get("sell", "#d62728")

    latest_trade_date = None
    trade_table_rows: List[Dict[str, Any]] = []

    if trades:
        trade_points = []
        for trade in trades:
            trade_time = pd.to_datetime(trade["time"])
            trade_date = str(trade_time.date())
            if latest_trade_date is None or trade_date > latest_trade_date:
                latest_trade_date = trade_date

            try:
                idx = df_account.index.get_indexer([trade_time], method="nearest")[0]
                account_return = df_account.iloc[idx]["return"]

                trade_points.append(
                    {
                        "time": trade_time,
                        "return": account_return,
                        "action": trade["action"],
                        "symbol": trade["symbol"],
                        "price": trade["price"],
                        "quantity": trade["quantity"],
                        "reason": trade.get("reason", ""),
                        "trade_tag": trade.get("trade_tag", ""),
                    }
                )
            except Exception as e:
                logger.warning(f"无法定位交易时间点 {trade_time}: {e}")
                continue

        if trade_points:
            df_trades = pd.DataFrame(trade_points)

            def _add_trade_markers(
                action: str, name: str, marker_symbol: str, color: str
            ):
                df_part = df_trades[df_trades["action"] == action]
                if df_part.empty:
                    return
                fig.add_trace(
                    go.Scatter(
                        x=df_part["time"],
                        y=df_part["return"],
                        mode="markers",
                        name=name,
                        marker=dict(symbol=marker_symbol, size=10, color=color),
                        customdata=df_part[
                            ["symbol", "price", "quantity", "reason", "trade_tag"]
                        ],
                        hovertemplate=(
                            f"<b>{name} %{{customdata[0]}}</b><br>"
                            "时间: %{x}<br>"
                            "价格: %{customdata[1]:.2f}<br>"
                            "数量: %{customdata[2]}<br>"
                            "标签: %{customdata[4]}<br>"
                            "原因: %{customdata[3]}<br>"
                            "当前收益率: %{y:.2%}"
                        ),
                    ),
                    row=1,
                    col=1,
                )

            _add_trade_markers(SignalType.BUY, "买入", "triangle-up", buy_color)
            _add_trade_markers(SignalType.SELL, "卖出", "triangle-down", sell_color)

            if latest_trade_date is not None and latest_trade_date != "":
                df_latest = df_trades[
                    df_trades["time"].dt.date.astype(str) == latest_trade_date
                ].copy()
                if not df_latest.empty:
                    latest_trade_rows: List[Dict[str, Any]] = []
                    for i in range(len(df_latest)):
                        row_series = df_latest.iloc[i]
                        latest_trade_rows.append(
                            {
                                "time": row_series["time"],
                                "symbol": row_series.get("symbol", ""),
                                "action": row_series.get("action", ""),
                                "price": row_series.get("price", 0.0),
                                "quantity": row_series.get("quantity", 0),
                                "trade_tag": row_series.get("trade_tag", ""),
                            }
                        )

                    latest_trade_rows.sort(
                        key=lambda x: pd.to_datetime(
                            cast(Any, x.get("time"))
                        ).to_pydatetime()
                    )

                    for r in latest_trade_rows:
                        trade_time = pd.to_datetime(
                            cast(Any, r.get("time"))
                        ).to_pydatetime()
                        trade_table_rows.append(
                            {
                                "time": trade_time.strftime("%H:%M"),
                                "symbol": str(r.get("symbol", "")),
                                "action": str(r.get("action", "")),
                                "qty": int(r.get("quantity", 0)),
                                "price": float(r.get("price", 0.0)),
                                "tag": str(r.get("trade_tag", "")),
                            }
                        )

    if (
        mdd_start_date is not None
        and mdd_end_date is not None
        and mdd_start_date != mdd_end_date
    ):
        fig.add_vrect(
            x0=mdd_start_date,
            x1=mdd_end_date,
            fillcolor="red",
            opacity=0.1,
            layer="below",
            line_width=0,
            annotation_text=f"最大回撤: {max_drawdown_val:.2%}",
            annotation_position="top left",
            row=cast(Any, 1),
            col=cast(Any, 1),
        )

        fig.add_trace(
            go.Scatter(
                x=[mdd_start_date, mdd_end_date],
                y=[mdd_start_return, mdd_end_return],
                mode="lines+markers",
                name="最大回撤",
                line=dict(color="red", width=2, dash="dot"),
                marker=dict(size=6, color="red"),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )

    if trade_table_rows:
        df_tbl = pd.DataFrame(trade_table_rows)
        fig.add_trace(
            go.Table(
                header=dict(
                    values=[
                        f"当日买卖({latest_trade_date})",
                        "代码",
                        "动作",
                        "数量",
                        "价格",
                        "标签",
                    ],
                    fill_color="#f0f0f0",
                    align="left",
                    font=dict(size=12),
                ),
                cells=dict(
                    values=[
                        df_tbl["time"],
                        df_tbl["symbol"],
                        df_tbl["action"],
                        df_tbl["qty"],
                        df_tbl["price"].map(lambda x: f"{x:.2f}"),
                        df_tbl["tag"],
                    ],
                    align="left",
                    height=22,
                ),
            ),
            row=1,
            col=2,
        )
    else:
        fig.add_trace(
            go.Table(
                header=dict(values=["当日买卖"], fill_color="#f0f0f0", align="left"),
                cells=dict(values=[["无交易记录"]], align="left"),
            ),
            row=1,
            col=2,
        )

    fig.update_layout(
        title=f"账户收益率 vs 基准指数 (最大回撤: {max_drawdown_val:.2%})",
        xaxis_title="时间",
        yaxis_title="累计收益率",
        yaxis=dict(tickformat=".2%"),
        hovermode="x unified",
        template="plotly_white",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(l=40, r=40, t=60, b=40),
    )

    fig.update_xaxes(title_text="时间", row=1, col=1)
    fig.update_yaxes(title_text="累计收益率", tickformat=".2%", row=1, col=1)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    filepath = os.path.join(output_dir, filename)
    fig.write_html(filepath)
    logger.info(f"收益率图表已保存至: {filepath}")

    return filepath
