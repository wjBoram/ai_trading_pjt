"""Plotly 재사용 캔들차트 컴포넌트"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render_candlestick(df: pd.DataFrame, ticker: str, title: str = "") -> go.Figure:
    """OHLCV + RSI 서브차트 렌더링"""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.2, 0.2],
        vertical_spacing=0.03,
        subplot_titles=("", "거래량", "RSI(14)"),
    )

    # 캔들스틱
    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name=ticker,
            increasing_line_color="#ef5350",
            decreasing_line_color="#26a69a",
        ),
        row=1, col=1,
    )

    # EMA 라인
    for col_name, color, label in [("ema5", "#ff9800", "EMA5"), ("ema20", "#2196f3", "EMA20"), ("ema60", "#9c27b0", "EMA60")]:
        if col_name in df.columns:
            fig.add_trace(
                go.Scatter(x=df["date"], y=df[col_name], mode="lines", name=label,
                           line=dict(color=color, width=1.2), opacity=0.8),
                row=1, col=1,
            )

    # 볼린저밴드
    if "bb_upper" in df.columns:
        fig.add_trace(
            go.Scatter(x=df["date"], y=df["bb_upper"], mode="lines", name="BB상단",
                       line=dict(color="rgba(100,100,100,0.4)", width=1, dash="dot")),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(x=df["date"], y=df["bb_lower"], mode="lines", name="BB하단",
                       line=dict(color="rgba(100,100,100,0.4)", width=1, dash="dot"),
                       fill="tonexty", fillcolor="rgba(100,100,100,0.05)"),
            row=1, col=1,
        )

    # 거래량
    colors = ["#ef5350" if c >= o else "#26a69a" for c, o in zip(df["close"], df["open"])]
    fig.add_trace(
        go.Bar(x=df["date"], y=df["volume"], marker_color=colors, name="거래량", opacity=0.7),
        row=2, col=1,
    )

    # RSI
    if "rsi" in df.columns:
        fig.add_trace(
            go.Scatter(x=df["date"], y=df["rsi"], mode="lines", name="RSI",
                       line=dict(color="#ff6b35", width=1.5)),
            row=3, col=1,
        )
        fig.add_hline(y=70, line_dash="dot", line_color="red", opacity=0.5, row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="blue", opacity=0.5, row=3, col=1)

    fig.update_layout(
        title=title or f"{ticker} 캔들차트",
        height=600,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        margin=dict(l=10, r=10, t=40, b=10),
    )
    fig.update_yaxes(title_text="가격 (원)", row=1, col=1)
    fig.update_yaxes(title_text="거래량", row=2, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=3, col=1)

    return fig
