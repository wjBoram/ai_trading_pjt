"""Page 2: 개별 종목 분석 (캔들차트 + 지표)"""

import streamlit as st

from core.database import get_session
from core.models import AgentSession
from dashboard.components.candlestick import render_candlestick
from data.data_manager import get_recent_news, get_recent_ohlcv
from data.pykrx_client import TOP_10_TICKERS
from indicators.technical import calculate_indicators, get_latest_indicators

st.set_page_config(page_title="종목 분석", layout="wide", page_icon="📈")
st.title("📈 종목 분석")

with st.sidebar:
    from dashboard.components.refresh_panel import render_refresh_panel
    render_refresh_panel(show_intraday=True, key_prefix="stock")

ticker_options = {v: k for k, v in TOP_10_TICKERS.items()}
selected_name = st.selectbox("종목 선택", list(ticker_options.keys()))
selected_ticker = ticker_options[selected_name]

period = st.slider("조회 기간 (일)", min_value=20, max_value=180, value=60, step=10)

df = get_recent_ohlcv(selected_ticker, days=period)

if df.empty:
    st.warning(f"{selected_name} 데이터 없음. DB 초기화(setup_db.py) 후 재시도")
    st.stop()

df_with_ind = calculate_indicators(df)
indicators = get_latest_indicators(df_with_ind)

# 상단 지표 요약
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    price = indicators.get("close", 0)
    ret = indicators.get("return_1d", 0) or 0
    st.metric("현재가", f"₩{price:,.0f}", delta=f"{ret*100:+.2f}%")
with col2:
    rsi = indicators.get("rsi")
    color = "🔴" if rsi and rsi > 70 else "🔵" if rsi and rsi < 30 else "⚪"
    st.metric("RSI(14)", f"{rsi:.1f} {color}" if rsi else "N/A")
with col3:
    macd_hist = indicators.get("macd_hist")
    st.metric("MACD Hist", f"{macd_hist:+.1f}" if macd_hist else "N/A")
with col4:
    vol_ratio = indicators.get("volume_ratio")
    st.metric("거래량비율", f"{vol_ratio:.2f}x" if vol_ratio else "N/A")
with col5:
    pos_52w = indicators.get("price_position_52w")
    st.metric("52주 최고가 대비", f"{pos_52w*100:.1f}%" if pos_52w else "N/A")

# 캔들차트
fig = render_candlestick(df_with_ind, selected_ticker, f"{selected_name} ({selected_ticker})")
st.plotly_chart(fig, use_container_width=True)

# AI 최근 신호
st.subheader("AI 최근 분석")
with get_session() as session:
    recent_session = (
        session.query(AgentSession)
        .filter_by(ticker=selected_ticker)
        .order_by(AgentSession.created_at.desc())
        .first()
    )

if recent_session:
    sig_colors = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
    sig_icon = sig_colors.get(recent_session.final_signal, "⚪")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("최근 AI 신호", f"{sig_icon} {recent_session.final_signal}")
    with col_b:
        st.metric("신뢰도", f"{(recent_session.final_confidence or 0):.0%}")
    with col_c:
        st.metric("가중 점수", f"{(recent_session.weighted_score or 0):+.3f}")
    st.caption(f"분석일: {recent_session.session_date} | 종료 사유: {recent_session.exit_reason}")
else:
    st.info("아직 AI 분석 결과 없음")

# 최근 뉴스
st.subheader("최근 뉴스")
news = get_recent_news(selected_ticker, max_articles=8)
if news:
    for n in news:
        st.markdown(f"- **{n['title']}** ({str(n['published_at'])[:10]})")
else:
    st.info("뉴스 없음")
