"""Page 5: 설정 및 시스템 상태"""

import streamlit as st

from agents.local_cli_runner import check_cli_available
from config.settings import settings

st.set_page_config(page_title="설정", layout="wide", page_icon="⚙️")
st.title("⚙️ 설정 및 시스템 상태")

# CLI 상태
st.subheader("AI CLI 상태")
cli_status = check_cli_available()

col1, col2 = st.columns(2)
with col1:
    if cli_status["claude"]:
        st.success("Claude Code CLI: 설치됨 ✅")
    else:
        st.error("Claude Code CLI: 미설치 ❌")
        st.code("npm install -g @anthropic-ai/claude-code")
with col2:
    if cli_status["codex"]:
        st.success("Codex CLI: 설치됨 ✅")
    else:
        st.error("Codex CLI: 미설치 ❌")
        st.code("npm install -g @openai/codex")

st.divider()

# 거래 모드
st.subheader("거래 설정")
st.info(f"현재 거래 모드: **{'실거래 🔴' if settings.is_live_trading else '모의거래 🟡'}**")
st.warning("거래 모드 변경은 .env 파일의 TRADING_MODE 값을 수정하세요. (paper → live)")

st.divider()

# AI 에이전트 설정 (읽기 전용)
st.subheader("AI 에이전트 설정")
col_a, col_b = st.columns(2)
with col_a:
    st.metric("최대 토론 라운드", settings.max_rounds)
    st.metric("합의 신뢰도 임계값", f"{settings.convergence_conf:.0%}")
    st.metric("신뢰도 하한", f"{settings.min_confidence:.0%}")
with col_b:
    st.metric("라운드 타임아웃", f"{settings.timeout_per_round}초")
    st.metric("오실레이션 감지 윈도우", f"{settings.oscillation_window}라운드")
    st.metric("최소 거래 신뢰도", f"{settings.min_trade_confidence:.0%}")

st.divider()

# 리스크 설정 (읽기 전용)
st.subheader("리스크 관리 설정")
col_r1, col_r2 = st.columns(2)
with col_r1:
    st.metric("종목당 최대 비중", f"{settings.max_position_pct:.0%}")
    st.metric("손절선", f"-{settings.stop_loss_pct:.0%}")
with col_r2:
    st.metric("일일 손실 한도", f"-{settings.daily_loss_limit_pct:.0%}")
    st.metric("최대 보유 종목 수", settings.max_open_positions)

st.caption("설정 변경은 .env 파일을 수정 후 서비스를 재시작하세요.")

st.divider()

# DB 현황
st.subheader("데이터베이스 현황")
from core.database import get_session
from core.models import OHLCVDaily, AgentSession, Trade, Stock

with get_session() as session:
    stock_count = session.query(Stock).count()
    ohlcv_count = session.query(OHLCVDaily).count()
    session_count = session.query(AgentSession).count()
    trade_count = session.query(Trade).count()

col_d1, col_d2, col_d3, col_d4 = st.columns(4)
with col_d1:
    st.metric("등록 종목", f"{stock_count}개")
with col_d2:
    st.metric("OHLCV 레코드", f"{ohlcv_count:,}건")
with col_d3:
    st.metric("AI 토론 세션", f"{session_count}건")
with col_d4:
    st.metric("매매 이력", f"{trade_count}건")
