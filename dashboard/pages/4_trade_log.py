"""Page 4: 매매 이력"""

import pandas as pd
import plotly.express as px
import streamlit as st

from core.database import get_session
from core.models import Trade

st.set_page_config(page_title="매매 이력", layout="wide", page_icon="📋")
st.title("📋 매매 이력")

# 필터
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    trade_type = st.radio("거래 유형", ["모의거래", "실거래", "전체"], horizontal=True)
with col_f2:
    signal_filter = st.multiselect("AI 신호 필터", ["BUY", "SELL", "STOP_LOSS", "없음"])
with col_f3:
    limit = st.slider("최대 표시 건수", 20, 200, 50, 10)

with get_session() as session:
    query = session.query(Trade)
    if trade_type == "모의거래":
        query = query.filter_by(paper=True)
    elif trade_type == "실거래":
        query = query.filter_by(paper=False)

    trades = query.order_by(Trade.executed_at.desc()).limit(limit).all()

if not trades:
    st.info("매매 이력 없음")
    st.stop()

records = [
    {
        "날짜": str(t.executed_at)[:16],
        "종목": t.ticker,
        "매매": t.side,
        "수량": t.quantity,
        "가격": f"₩{t.price:,.0f}",
        "금액": f"₩{t.total_amount:,.0f}",
        "손익": f"₩{t.pnl:+,.0f}" if t.pnl is not None else "-",
        "AI신호": t.ai_signal or "-",
        "신뢰도": f"{t.ai_confidence:.0%}" if t.ai_confidence else "-",
        "유형": "모의" if t.paper else "실거래",
    }
    for t in trades
]

df_trades = pd.DataFrame(records)
st.dataframe(df_trades, use_container_width=True, hide_index=True)

# 요약
st.divider()
col_a, col_b, col_c = st.columns(3)
realized_pnl = sum(t.pnl or 0 for t in trades if t.side == "SELL")
wins = sum(1 for t in trades if t.side == "SELL" and (t.pnl or 0) > 0)
total_sells = sum(1 for t in trades if t.side == "SELL")

with col_a:
    st.metric("실현 손익 합계", f"₩{realized_pnl:+,.0f}")
with col_b:
    st.metric("매도 건수", f"{total_sells}건")
with col_c:
    win_rate = wins / total_sells if total_sells > 0 else 0
    st.metric("승률", f"{win_rate:.0%}")

# CSV 다운로드
csv = df_trades.to_csv(index=False, encoding="utf-8-sig")
st.download_button("CSV 내보내기", csv, "trades.csv", "text/csv")
