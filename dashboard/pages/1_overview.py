"""Page 1: 포트폴리오 전체 현황"""

import time

import plotly.express as px
import streamlit as st

from config.settings import settings
from core.database import get_session
from core.models import PortfolioSnapshot
from trading.portfolio import get_portfolio_state

st.set_page_config(page_title="포트폴리오 현황", layout="wide", page_icon="📊")
st.title("📊 포트폴리오 현황")

mode_badge = "🔴 실거래" if settings.is_live_trading else "🟡 모의거래"
st.caption(f"거래 모드: {mode_badge}")

# 사이드바: 수기 갱신 패널
with st.sidebar:
    from dashboard.components.refresh_panel import render_refresh_panel
    render_refresh_panel(key_prefix="overview")


def load_portfolio():
    return get_portfolio_state()


def load_snapshots():
    with get_session() as session:
        records = (
            session.query(PortfolioSnapshot)
            .order_by(PortfolioSnapshot.snapshot_date)
            .limit(180)
            .all()
        )
        return [
            {
                "date": str(r.snapshot_date),
                "total_value": r.total_value,
                "daily_pnl": r.daily_pnl,
                "total_pnl": r.total_pnl,
            }
            for r in records
        ]


portfolio = load_portfolio()
snapshots = load_snapshots()

# 상단 지표
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("총 자산", f"₩{portfolio['total_value']:,.0f}")
with col2:
    st.metric("가용 현금", f"₩{portfolio['cash']:,.0f}")
with col3:
    daily = portfolio["daily_pnl"]
    st.metric("오늘 손익", f"₩{daily:+,.0f}", delta=f"{daily / max(portfolio['total_value'], 1) * 100:+.2f}%")
with col4:
    total = portfolio["total_pnl"]
    st.metric("누적 손익", f"₩{total:+,.0f}")

st.divider()

# 자산 추이 차트
if snapshots:
    import pandas as pd
    df_snap = pd.DataFrame(snapshots)
    fig = px.line(df_snap, x="date", y="total_value", title="자산 추이", template="plotly_dark")
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("포트폴리오 스냅샷 데이터 없음 (장 마감 후 자동 저장됩니다)")

# 보유 포지션
st.subheader("보유 포지션")
positions = portfolio["positions"]
if positions:
    import pandas as pd
    df_pos = pd.DataFrame(positions)
    df_pos["미실현손익"] = df_pos["unrealized_pnl"].apply(lambda x: f"₩{x:+,.0f}")
    df_pos["수익률"] = df_pos["unrealized_pnl_pct"].apply(lambda x: f"{x*100:+.2f}%")
    df_pos["현재가"] = df_pos["current_price"].apply(lambda x: f"₩{x:,.0f}")
    df_pos["평균매입가"] = df_pos["avg_cost"].apply(lambda x: f"₩{x:,.0f}")
    st.dataframe(
        df_pos[["ticker", "quantity", "평균매입가", "현재가", "미실현손익", "수익률"]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("현재 보유 종목 없음")

# 30초마다 자동 갱신 (장중에만)
from scheduler.tasks import is_market_open
if is_market_open():
    time.sleep(30)
    st.rerun()
