"""Page 3: AI 듀얼 에이전트 토론 뷰어"""

import streamlit as st

from core.database import get_session
from core.models import AgentRound, AgentSession
from dashboard.components.debate_viewer import render_agent_round, render_consensus_box
from data.pykrx_client import TOP_10_TICKERS

st.set_page_config(page_title="AI 토론 뷰어", layout="wide", page_icon="🤖")
st.title("🤖 AI 듀얼 에이전트 토론")
st.caption("Claude Code CLI ↔ Codex CLI 협의 과정 실시간 열람")

# 세션 선택
with get_session() as session:
    sessions = session.query(AgentSession).order_by(AgentSession.created_at.desc()).limit(50).all()

if not sessions:
    st.info("아직 AI 토론 세션 없음. 스케줄러(09:10 KST)가 실행되면 자동 생성됩니다.")

    # 수동 실행 버튼
    st.subheader("수동 분석 실행")
    col_ticker, col_btn = st.columns([3, 1])
    with col_ticker:
        ticker_options = {v: k for k, v in TOP_10_TICKERS.items()}
        selected_name = st.selectbox("분석 종목", list(ticker_options.keys()))
        selected_ticker = ticker_options[selected_name]
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("AI 분석 실행", type="primary")

    if run_btn:
        with st.spinner(f"{selected_name} AI 토론 진행 중... (최대 {5 * 120}초)"):
            from agents.orchestrator import get_recent_sessions, run_debate, save_session_to_db
            from agents.protocol import MarketContext
            from data.data_manager import get_recent_news, get_recent_ohlcv
            from data.pykrx_client import get_current_price
            from data.sentiment import aggregate_sentiment
            from indicators.technical import get_latest_indicators
            from scheduler.tasks import job_morning_analysis

            df = get_recent_ohlcv(selected_ticker, days=60)
            if df.empty:
                st.error("데이터 없음")
            else:
                indicators = get_latest_indicators(df) or {}
                news = get_recent_news(selected_ticker, max_articles=8)
                ctx = MarketContext(
                    ticker=selected_ticker,
                    company_name=selected_name,
                    current_price=get_current_price(selected_ticker) or indicators.get("close", 0),
                    day_change_pct=float(indicators.get("return_1d") or 0) * 100,
                    ohlcv_20d=df.tail(20).to_dict("records"),
                    indicators=indicators,
                    news_headlines=[n["title"] for n in news],
                    volume_ratio=float(indicators.get("volume_ratio") or 1.0),
                    market_date=str(df["date"].iloc[-1]),
                    news_sentiment=aggregate_sentiment([n["sentiment_score"] for n in news]),
                    prior_sessions=get_recent_sessions(selected_ticker),
                )
                result = run_debate(ctx)
                save_session_to_db(selected_ticker, result)
                st.success("분석 완료! 페이지를 새로고침하세요.")
                st.rerun()
    st.stop()

# 세션 선택 UI
session_labels = [
    f"{s.ticker} ({TOP_10_TICKERS.get(s.ticker, s.ticker)}) | {s.session_date} | {s.final_signal} | {(s.final_confidence or 0):.0%} | {s.exit_reason}"
    for s in sessions
]
selected_idx = st.selectbox(
    "분석 세션 선택", range(len(session_labels)), format_func=lambda i: session_labels[i]
)
selected_session = sessions[selected_idx]

# 세션 라운드 로드
with get_session() as session:
    rounds = (
        session.query(AgentRound)
        .filter_by(session_id=selected_session.id)
        .order_by(AgentRound.round_number)
        .all()
    )
    rounds_data = [
        {
            "round_number": r.round_number,
            "agent": r.agent,
            "signal": r.signal,
            "confidence": r.confidence,
            "reasoning": r.reasoning,
            "key_factors": r.key_factors,
            "risk_level": r.risk_level,
            "agreement": r.agreement,
            "disagreement_points": r.disagreement_points,
            "signal_changed": r.signal_changed,
        }
        for r in rounds
    ]

# 토론 라운드 표시 (최대 3열)
if rounds_data:
    n = len(rounds_data)
    cols_per_row = min(n, 3)
    for row_start in range(0, n, cols_per_row):
        row_rounds = rounds_data[row_start : row_start + cols_per_row]
        cols = st.columns(len(row_rounds))
        for col, rnd in zip(cols, row_rounds):
            with col:
                render_agent_round(rnd, rnd["round_number"] - 1)
else:
    st.info("라운드 데이터 없음")

# 최종 합의 박스
session_dict = {
    "final_signal": selected_session.final_signal,
    "final_confidence": selected_session.final_confidence,
    "weighted_score": selected_session.weighted_score,
    "exit_reason": selected_session.exit_reason,
    "execute_trade": selected_session.execute_trade,
    "buy_price": selected_session.buy_price,
    "sell_price": selected_session.sell_price,
}
render_consensus_box(session_dict)
