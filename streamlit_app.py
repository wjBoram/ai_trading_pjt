"""Streamlit 대시보드 진입점"""

import streamlit as st

from config.logging_config import setup_logging
from config.settings import settings
from core.database import init_db

# 초기화 (앱 시작 시 1회)
if "initialized" not in st.session_state:
    setup_logging(settings.log_level, settings.log_file)
    init_db()
    st.session_state["initialized"] = True

st.set_page_config(
    page_title="국내주식 AI 자동매매",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📈 국내주식 AI 자동매매 시스템")
st.markdown("""
### 시스템 소개
- **Claude Code CLI** ↔ **Codex CLI** 듀얼 AI 토론으로 매매 신호 생성
- KOSPI/KOSDAQ 상위 10개 종목 자동 분석
- 리스크 관리 내장 (손절, 포지션 한도, 일일 손실 한도)

### 메뉴 (좌측 사이드바)
| 페이지 | 설명 |
|--------|------|
| 📊 Overview | 포트폴리오 현황·손익 |
| 📈 Stock Analysis | 종목별 캔들차트·지표 |
| 🤖 AI Debate | AI 토론 라운드 뷰어 |
| 📋 Trade Log | 매매 이력 |
| ⚙️ Settings | 설정·시스템 상태 |
""")

mode_badge = "🔴 실거래" if settings.is_live_trading else "🟡 모의거래"
st.sidebar.caption(f"모드: {mode_badge}")
