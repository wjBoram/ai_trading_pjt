"""AI 토론 라운드 표시 컴포넌트"""

import json

import streamlit as st


def render_agent_round(round_data: dict, index: int) -> None:
    """단일 라운드 카드 렌더링"""
    agent = round_data.get("agent", "")
    signal = round_data.get("signal", "HOLD")
    confidence = round_data.get("confidence", 0.0)
    reasoning = round_data.get("reasoning", "")
    key_factors_raw = round_data.get("key_factors", "[]")
    risk_level = round_data.get("risk_level", "medium")
    agreement = round_data.get("agreement")
    disagreement_raw = round_data.get("disagreement_points", "[]")
    signal_changed = round_data.get("signal_changed")

    try:
        key_factors = json.loads(key_factors_raw) if isinstance(key_factors_raw, str) else key_factors_raw
        disagreements = json.loads(disagreement_raw) if isinstance(disagreement_raw, str) else disagreement_raw
    except (json.JSONDecodeError, TypeError):
        key_factors = []
        disagreements = []

    agent_label = "Claude" if agent == "claude" else "Codex"
    agent_icon = "" if agent == "claude" else ""

    signal_colors = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
    signal_icon = signal_colors.get(signal, "⚪")

    with st.container(border=True):
        col_header, col_signal = st.columns([3, 1])
        with col_header:
            st.markdown(f"**Round {round_data.get('round_number', index + 1)}: {agent_icon} {agent_label}**")
        with col_signal:
            st.markdown(f"### {signal_icon} {signal}")

        st.progress(confidence, text=f"신뢰도: {confidence:.0%}")

        risk_colors = {"low": "🟦", "medium": "🟨", "high": "🟥"}
        st.caption(f"리스크 레벨: {risk_colors.get(risk_level, '⬜')} {risk_level.upper()}")

        with st.expander("분석 근거", expanded=(index < 2)):
            st.write(reasoning)

        if key_factors:
            st.markdown("**핵심 요인:**")
            for f in key_factors:
                st.markdown(f"- {f}")

        if agreement is not None:
            if agreement:
                st.success("이전 분석에 동의")
            else:
                st.warning("이전 분석에 반박")
                if disagreements:
                    for d in disagreements:
                        st.markdown(f"  ⚠️ {d}")

        if signal_changed is not None:
            if signal_changed:
                st.info("신호 변경됨")
            else:
                st.caption("신호 유지")


def render_consensus_box(session: dict) -> None:
    """최종 합의 박스"""
    final_signal = session.get("final_signal", "HOLD")
    final_confidence = session.get("final_confidence", 0.0)
    weighted_score = session.get("weighted_score", 0.0)
    exit_reason = session.get("exit_reason", "")
    execute_trade = session.get("execute_trade", False)
    buy_price = session.get("buy_price")
    sell_price = session.get("sell_price")

    st.divider()
    st.subheader("최종 합의 결과")

    exit_labels = {
        "CONSENSUS": "✅ 합의 달성",
        "MAX_ROUNDS": "⏱️ 최대 라운드 도달",
        "OSCILLATION": "🔄 오실레이션 (교착상태)",
        "TIMEOUT": "⏰ 타임아웃",
        "LOW_CONFIDENCE": "📉 신뢰도 하한 미달",
        "CLI_ERROR": "❌ CLI 오류",
    }

    col1, col2, col3 = st.columns(3)
    with col1:
        signal_colors = {"BUY": "normal", "SELL": "inverse", "HOLD": "off"}
        delta_label = {"BUY": "매수 신호", "SELL": "매도 신호", "HOLD": "관망"}.get(final_signal, "")
        st.metric("최종 신호", final_signal, delta=delta_label)
    with col2:
        st.metric("최종 신뢰도", f"{final_confidence:.0%}")
    with col3:
        st.metric("가중 점수", f"{weighted_score:+.3f}")

    st.caption(f"종료 사유: {exit_labels.get(exit_reason, exit_reason)}")

    if execute_trade:
        st.success(f"거래 실행 예정")
        if buy_price:
            st.caption(f"매수 목표가: {buy_price:,.0f}원 | 매도 목표가: {sell_price:,.0f}원")
    else:
        st.info("거래 미실행 (신뢰도 부족 또는 안전 조건 미충족)")
