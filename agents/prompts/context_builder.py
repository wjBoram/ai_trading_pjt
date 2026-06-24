"""MarketContext → 프롬프트 문자열 변환"""

import json

from agents.protocol import AgentMessage, MarketContext, PriorSessionSummary


def build_market_context_text(ctx: MarketContext) -> str:
    """시장 컨텍스트를 읽기 쉬운 텍스트로 변환"""
    ohlcv_rows = []
    for row in ctx.ohlcv_20d[-20:]:
        ohlcv_rows.append(
            f"  {row['date']}: 시가{row['open']:,.0f} 고가{row['high']:,.0f} "
            f"저가{row['low']:,.0f} 종가{row['close']:,.0f} 거래량{row['volume']:,.0f}"
        )

    ind = ctx.indicators
    indicators_text = f"""
  RSI(14): {ind.get("rsi", "N/A")}
  MACD: {ind.get("macd", "N/A")} / Signal: {ind.get("macd_signal", "N/A")} / Hist: {ind.get("macd_hist", "N/A")}
  볼린저밴드: 상단{ind.get("bb_upper", "N/A"):} / 중간{ind.get("bb_mid", "N/A")} / 하단{ind.get("bb_lower", "N/A")}
  EMA5: {ind.get("ema5", "N/A")} / EMA20: {ind.get("ema20", "N/A")} / EMA60: {ind.get("ema60", "N/A")}
  ATR(%): {ind.get("atr_pct", "N/A")}
  거래량비율: {ind.get("volume_ratio", "N/A")}
  Stochastic K: {ind.get("stoch_k", "N/A")} / D: {ind.get("stoch_d", "N/A")}
  수익률 1일: {ind.get("return_1d", "N/A")} / 5일: {ind.get("return_5d", "N/A")} / 20일: {ind.get("return_20d", "N/A")} / 60일(중기 모멘텀): {ind.get("return_60d", "N/A")}
  52주 최고가 대비 위치: {ind.get("price_position_52w", "N/A")}
  이격도(EMA20 대비, 100=평균): {ind.get("disparity_ema20", "N/A")}"""

    news_text = (
        "\n".join(f"  - {h}" for h in ctx.news_headlines) if ctx.news_headlines else "  (뉴스 없음)"
    )
    sentiment_text = (
        f"{ctx.news_sentiment:+.2f} (-1.0 매우 부정 ~ +1.0 매우 긍정)"
        if ctx.news_sentiment is not None
        else "N/A"
    )
    prior_sessions_text = build_prior_sessions_text(ctx.prior_sessions)

    return f"""[분석 대상 종목]
종목: {ctx.company_name} ({ctx.ticker})
분석 기준일: {ctx.market_date}
현재가: {ctx.current_price:,.0f}원 (당일 등락: {ctx.day_change_pct:+.2f}%)
거래량 비율: {ctx.volume_ratio:.2f}x (20일 평균 대비)

[최근 20일 일봉 (OHLCV)]
{chr(10).join(ohlcv_rows)}

[기술적 지표]
{indicators_text}

[최근 뉴스 헤드라인] (감성 점수 평균: {sentiment_text})
{news_text}

[과거 분석 이력 (동일 종목, 최신순)]
{prior_sessions_text}"""


def build_prior_sessions_text(prior_sessions: list[PriorSessionSummary]) -> str:
    """동일 종목의 과거 토론 세션 요약 텍스트 (세션 간 연속성)"""
    if not prior_sessions:
        return "  (과거 분석 이력 없음 - 첫 분석)"

    lines = []
    for s in prior_sessions:
        reasoning = s.last_reasoning[:150] + ("..." if len(s.last_reasoning) > 150 else "")
        lines.append(
            f"  - {s.session_date}: {s.final_signal.value} "
            f"(신뢰도 {s.final_confidence:.0%}, 종료조건 {s.exit_reason.value}) "
            f"— {reasoning or '(근거 없음)'}"
        )
    return "\n".join(lines)


def build_history_text(messages: list[AgentMessage]) -> str:
    """이전 라운드 대화 히스토리 텍스트"""
    if not messages:
        return "(이전 라운드 없음)"

    lines = []
    for msg in messages:
        agent_label = "Claude" if msg.agent == "claude" else "Codex"
        factors = "\n    ".join(f"- {f}" for f in msg.key_factors) if msg.key_factors else "(없음)"
        disagreements = ""
        if msg.disagreement_points:
            disagreements = "\n  반박 포인트:\n    " + "\n    ".join(
                f"- {d}" for d in msg.disagreement_points
            )

        lines.append(f"""--- Round {msg.round_number}: {agent_label} ---
  신호: {msg.signal.value} (신뢰도: {msg.confidence:.0%})
  리스크: {msg.risk_level.value if msg.risk_level else "N/A"}
  근거: {msg.reasoning[:300]}{"..." if len(msg.reasoning) > 300 else ""}
  핵심 요인:
    {factors}{disagreements}""")

    return "\n\n".join(lines)
