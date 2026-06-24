"""수기 데이터 갱신 패널 컴포넌트 (모든 페이지에서 재사용)"""

import streamlit as st


def render_refresh_panel(
    tickers: list[str] | None = None,
    show_intraday: bool = True,
    key_prefix: str = "",
) -> None:
    """사이드바 또는 메인 영역에 수기 갱신 UI 렌더링"""

    with st.expander("🔄 데이터 수기 갱신", expanded=False):
        st.caption("배치 스케줄과 무관하게 즉시 데이터를 갱신합니다.")

        col1, col2 = st.columns(2)

        with col1:
            refresh_ohlcv = st.checkbox("일봉(OHLCV)", value=True, key=f"{key_prefix}_ohlcv")
            refresh_news = st.checkbox("뉴스", value=True, key=f"{key_prefix}_news")

        with col2:
            trigger_ai = st.toggle(
                "갱신 후 AI 즉시 분석",
                value=True,
                key=f"{key_prefix}_trigger_ai",
                help="켜면 데이터 갱신 직후 AI 토론을 자동 실행합니다",
            )

        if show_intraday:
            interval = st.select_slider(
                "분봉·시간봉",
                options=["1m", "5m", "10m", "30m", "60m", "1d", "❌ 미포함"],
                value="5m",
                key=f"{key_prefix}_interval",
            )

        if st.button("지금 갱신", type="primary", key=f"{key_prefix}_btn"):
            data_types = []
            if refresh_ohlcv:
                data_types.append("ohlcv")
            if refresh_news:
                data_types.append("news")

            if not data_types and (not show_intraday or interval == "❌ 미포함"):
                st.warning("갱신할 데이터 유형을 하나 이상 선택하세요")
                return

            with st.spinner("데이터 갱신 중..."):
                from data.realtime_collector import refresh_manager

                result = refresh_manager.refresh_now(
                    tickers=tickers,
                    data_types=data_types if data_types else None,
                    trigger_analysis=trigger_ai,
                )

                # 분봉 갱신
                if show_intraday and interval != "❌ 미포함":
                    intraday_result = refresh_manager.refresh_intraday_batch(
                        interval=interval,
                        trigger_analysis=False,  # 중복 방지
                    )
                    result["intraday"] = intraday_result

            if result.get("refreshed"):
                st.success(f"갱신 완료: {', '.join(result['refreshed'])}")
            if result.get("analysis_triggered"):
                st.info(f"AI 분석 트리거: {', '.join(result['analysis_triggered'])} (백그라운드 실행)")
            if result.get("failed"):
                st.error(f"갱신 실패: {', '.join(result['failed'])}")

        # 마지막 갱신 시각
        from data.realtime_collector import refresh_manager
        from data.pykrx_client import TOP_10_TICKERS

        last_times = [
            (TOP_10_TICKERS.get(t, t), refresh_manager.get_last_refresh_time(t))
            for t in (tickers or list(TOP_10_TICKERS.keys()))
        ]
        never_refreshed = [name for name, t in last_times if t is None]
        if never_refreshed:
            st.caption(f"아직 갱신 안 됨: {', '.join(never_refreshed[:3])}{'...' if len(never_refreshed) > 3 else ''}")
