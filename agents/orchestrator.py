"""AI 듀얼 에이전트 오케스트레이터 - 적응형 토론 루프"""

import json
from datetime import date
from typing import Optional

import structlog

from agents.local_cli_runner import AgentTimeoutError, extract_json_from_response, run_agent
from agents.prompts import claude_initial, codex_review, negotiation
from agents.protocol import (
    AgentMessage,
    ConsensusResult,
    ExitReason,
    MarketContext,
    PriorSessionSummary,
    RiskLevel,
    Signal,
)
from config.settings import settings
from core.database import get_session
from core.exceptions import AgentError, AgentParseError
from core.models import AgentRound, AgentSession

logger = structlog.get_logger(__name__)


def run_debate(ctx: MarketContext) -> ConsensusResult:
    """3~5 라운드 적응형 토론 실행

    수렴·중단 조건:
      A. 신뢰도 하한 미달 → HOLD 강제
      B. 합의 달성 → 즉시 종료
      C. Codex 불확실 → HOLD 강제
      D. 오실레이션 → HOLD 강제
      E. 최대 라운드 → 가중 평균으로 결론
      F. CLI 타임아웃 → HOLD 강제
    """
    messages: list[AgentMessage] = []
    exit_reason: Optional[ExitReason] = None
    forced_hold = False

    # Round 1: Claude 초기 분석
    round1_msg = _run_round(
        agent="claude",
        round_number=1,
        ctx=ctx,
        prior_messages=[],
    )
    if round1_msg is None:
        return _make_forced_result(ExitReason.CLI_ERROR, messages, ctx)

    messages.append(round1_msg)
    logger.info(
        "Round 1 완료", agent="claude", signal=round1_msg.signal.value, conf=round1_msg.confidence
    )

    # 조건 A: Claude 신뢰도 하한
    if round1_msg.confidence < settings.min_confidence:
        logger.warning("조건A 발동 - Claude 신뢰도 하한 미달", conf=round1_msg.confidence)
        return _make_forced_result(ExitReason.LOW_CONFIDENCE, messages, ctx)

    # Round 2: Codex 검토
    round2_msg = _run_round(
        agent="codex",
        round_number=2,
        ctx=ctx,
        prior_messages=messages,
    )
    if round2_msg is None:
        return _make_forced_result(ExitReason.CLI_ERROR, messages, ctx)

    messages.append(round2_msg)
    logger.info(
        "Round 2 완료", agent="codex", signal=round2_msg.signal.value, conf=round2_msg.confidence
    )

    # 조건 C: Codex 신뢰도 하한
    if round2_msg.confidence < settings.min_confidence:
        logger.warning("조건C 발동 - Codex 신뢰도 하한 미달", conf=round2_msg.confidence)
        return _make_forced_result(ExitReason.LOW_CONFIDENCE, messages, ctx)

    # 조건 B: Round 2에서 합의 달성
    if _check_consensus(messages):
        logger.info("조건B 발동 - Round 2에서 합의 달성")
        return _make_consensus_result(messages, ctx)

    # Round 3~MAX_ROUNDS: 협상 라운드
    for round_num in range(3, settings.max_rounds + 1):
        # 홀수 = Claude, 짝수 = Codex
        current_agent = "claude" if round_num % 2 == 1 else "codex"

        try:
            msg = _run_round(
                agent=current_agent,
                round_number=round_num,
                ctx=ctx,
                prior_messages=messages,
            )
        except AgentTimeoutError:
            logger.error("조건F 발동 - CLI 타임아웃", round=round_num, agent=current_agent)
            return _make_forced_result(ExitReason.TIMEOUT, messages, ctx)

        if msg is None:
            return _make_forced_result(ExitReason.CLI_ERROR, messages, ctx)

        messages.append(msg)
        logger.info(
            f"Round {round_num} 완료",
            agent=current_agent,
            signal=msg.signal.value,
            conf=msg.confidence,
        )

        # 조건 A: 신뢰도 하한
        if msg.confidence < settings.min_confidence:
            logger.warning(f"조건A 발동 - Round {round_num} 신뢰도 하한 미달", conf=msg.confidence)
            return _make_forced_result(ExitReason.LOW_CONFIDENCE, messages, ctx)

        # 조건 D: 오실레이션 감지
        if _detect_oscillation(messages):
            logger.warning("조건D 발동 - 오실레이션 감지 (교착상태)")
            return _make_forced_result(ExitReason.OSCILLATION, messages, ctx)

        # 조건 B: 합의 달성
        if _check_consensus(messages):
            logger.info(f"조건B 발동 - Round {round_num}에서 합의 달성")
            return _make_consensus_result(messages, ctx)

    # 조건 E: 최대 라운드 도달
    logger.warning("조건E 발동 - 최대 라운드 도달", max_rounds=settings.max_rounds)
    return _make_weighted_result(messages, ctx, ExitReason.MAX_ROUNDS)


def _run_round(
    agent: str,
    round_number: int,
    ctx: MarketContext,
    prior_messages: list[AgentMessage],
) -> Optional[AgentMessage]:
    """단일 라운드 실행 및 응답 파싱"""
    try:
        if round_number == 1:
            prompt = claude_initial.build_prompt(ctx)
        elif round_number == 2:
            prompt = codex_review.build_prompt(ctx, prior_messages)
        else:
            prompt = negotiation.build_prompt(ctx, prior_messages, agent, round_number)

        raw_response = run_agent(agent, prompt, timeout_sec=settings.timeout_per_round)
        return _parse_agent_response(raw_response, agent, round_number)

    except AgentTimeoutError:
        raise
    except Exception as e:
        logger.error("라운드 실행 실패", round=round_number, agent=agent, error=str(e))
        return None


def _parse_agent_response(raw: str, agent: str, round_number: int) -> Optional[AgentMessage]:
    """AI 응답 JSON 파싱"""
    data = extract_json_from_response(raw)
    if not data:
        logger.error("JSON 파싱 실패", agent=agent, round=round_number, raw_preview=raw[:200])
        return None

    try:
        signal_val = data.get("signal", "HOLD").upper()
        signal = Signal(signal_val) if signal_val in Signal._value2member_map_ else Signal.HOLD

        risk_val = data.get("risk_level", "medium").lower()
        risk = RiskLevel(risk_val) if risk_val in RiskLevel._value2member_map_ else RiskLevel.MEDIUM

        return AgentMessage(
            round_number=round_number,
            agent=agent,
            signal=signal,
            confidence=float(data.get("confidence", 0.5)),
            reasoning=str(data.get("reasoning", "")),
            key_factors=list(data.get("key_factors", [])),
            risk_level=risk,
            agreement=data.get("agreement_with_prior"),
            disagreement_points=list(data.get("disagreement_points", [])),
            signal_changed=data.get("signal_changed"),
        )
    except Exception as e:
        logger.error("응답 파싱 오류", agent=agent, round=round_number, error=str(e))
        return None


def _check_consensus(messages: list[AgentMessage]) -> bool:
    """합의 달성 여부: 최신 claude·codex 신호 일치 + avg 신뢰도 임계값 이상"""
    if len(messages) < 2:
        return False

    latest_claude = next((m for m in reversed(messages) if m.agent == "claude"), None)
    latest_codex = next((m for m in reversed(messages) if m.agent == "codex"), None)

    if not latest_claude or not latest_codex:
        return False

    signals_match = latest_claude.signal == latest_codex.signal
    avg_conf = (latest_claude.confidence + latest_codex.confidence) / 2
    return signals_match and avg_conf >= settings.convergence_conf


def _detect_oscillation(messages: list[AgentMessage]) -> bool:
    """오실레이션 감지: 최근 N 라운드의 전체 신호 시퀀스가 교대 반복

    BUY→SELL→BUY 또는 SELL→BUY→SELL 패턴을 감지.
    에이전트 구분 없이 전체 신호 흐름을 기준으로 판단.
    """
    window = settings.oscillation_window
    if len(messages) < window:
        return False

    recent_signals = [m.signal for m in messages[-window:]]

    # HOLD만 있는 경우는 교착이 아님
    non_hold = [s for s in recent_signals if s != Signal.HOLD]
    if len(non_hold) < 2:
        return False

    # BUY↔SELL 교대 패턴: 연속 신호가 모두 다른 경우
    for i in range(1, len(non_hold)):
        if non_hold[i] == non_hold[i - 1]:
            return False  # 같은 신호 연속 → 교착 아님

    return True


def _calc_weighted_score(messages: list[AgentMessage]) -> tuple[float, float]:
    """가중 점수 계산 (최신 라운드 가중치 높음)"""
    if not messages:
        return 0.0, 0.0

    total_rounds = len(messages)
    weights = _exp_decay_weights(total_rounds)

    weighted_score = 0.0
    total_weight = 0.0
    weighted_conf = 0.0

    for i, msg in enumerate(messages):
        w = weights[i]
        weighted_score += w * msg.weighted_contribution
        weighted_conf += w * msg.confidence
        total_weight += w

    if total_weight == 0:
        return 0.0, 0.0

    return weighted_score / total_weight, weighted_conf / total_weight


def _exp_decay_weights(n: int) -> list[float]:
    """지수 감쇠 가중치 (최신 라운드 가중치 높음)"""
    import math

    weights = [math.exp(0.5 * i) for i in range(n)]
    total = sum(weights)
    return [w / total for w in weights]


def _score_to_signal(score: float) -> Signal:
    if score >= 0.35:
        return Signal.BUY
    elif score <= -0.35:
        return Signal.SELL
    return Signal.HOLD


def _calc_trade_prices(
    ctx: MarketContext, signal: Signal
) -> tuple[Optional[float], Optional[float]]:
    """AI 신호 기반 매수/매도 목표가 계산"""
    price = ctx.current_price
    atr_pct = ctx.indicators.get("atr_pct") or 0.015  # 기본 1.5%

    if signal == Signal.BUY:
        buy_price = round(price * (1 - atr_pct * 0.5))
        sell_price = round(price * (1 + atr_pct * 2.0))
        return buy_price, sell_price
    elif signal == Signal.SELL:
        buy_price = round(price * (1 - 0.05))  # 5% 하락 시 재매수 검토
        sell_price = round(price * 1.002)  # 소폭 프리미엄으로 매도
        return buy_price, sell_price
    return None, None


def _make_consensus_result(messages: list[AgentMessage], ctx: MarketContext) -> ConsensusResult:
    weighted_score, avg_conf = _calc_weighted_score(messages)
    final_signal = _score_to_signal(weighted_score)
    buy_price, sell_price = _calc_trade_prices(ctx, final_signal)

    execute_trade = avg_conf >= settings.convergence_conf and final_signal != Signal.HOLD

    return ConsensusResult(
        final_signal=final_signal,
        final_confidence=avg_conf,
        weighted_score=weighted_score,
        total_rounds=len(messages),
        exit_reason=ExitReason.CONSENSUS,
        agreement=True,
        execute_trade=execute_trade,
        buy_price=buy_price,
        sell_price=sell_price,
        messages=messages,
        rationale=messages[-1].reasoning if messages else "",
    )


def _make_weighted_result(
    messages: list[AgentMessage], ctx: MarketContext, reason: ExitReason
) -> ConsensusResult:
    weighted_score, avg_conf = _calc_weighted_score(messages)
    final_signal = _score_to_signal(weighted_score)
    buy_price, sell_price = _calc_trade_prices(ctx, final_signal)

    # 최대 라운드 도달은 신뢰도 충족 시만 거래
    execute_trade = (
        reason == ExitReason.MAX_ROUNDS
        and avg_conf >= settings.convergence_conf
        and final_signal != Signal.HOLD
    )

    return ConsensusResult(
        final_signal=final_signal,
        final_confidence=avg_conf,
        weighted_score=weighted_score,
        total_rounds=len(messages),
        exit_reason=reason,
        agreement=False,
        execute_trade=execute_trade,
        buy_price=buy_price,
        sell_price=sell_price,
        fallback_used=True,
        messages=messages,
        rationale=f"{reason.value}로 인한 강제 결론",
    )


def _make_forced_result(
    reason: ExitReason, messages: list[AgentMessage], ctx: MarketContext
) -> ConsensusResult:
    """HOLD 강제 종료"""
    avg_conf = sum(m.confidence for m in messages) / len(messages) if messages else 0.0
    return ConsensusResult(
        final_signal=Signal.HOLD,
        final_confidence=avg_conf,
        weighted_score=0.0,
        total_rounds=len(messages),
        exit_reason=reason,
        agreement=False,
        execute_trade=False,
        fallback_used=True,
        messages=messages,
        rationale=f"{reason.value}로 인한 HOLD 강제 종료",
    )


def save_session_to_db(ticker: str, result: ConsensusResult) -> int:
    """토론 결과 DB 저장, session_id 반환"""
    with get_session() as session:
        agent_session = AgentSession(
            ticker=ticker,
            session_date=date.today(),
            total_rounds=result.total_rounds,
            final_signal=result.final_signal.value,
            final_confidence=result.final_confidence,
            weighted_score=result.weighted_score,
            exit_reason=result.exit_reason.value,
            execute_trade=result.execute_trade,
            buy_price=result.buy_price,
            sell_price=result.sell_price,
        )
        session.add(agent_session)
        session.flush()

        for msg in result.messages:
            session.add(
                AgentRound(
                    session_id=agent_session.id,
                    round_number=msg.round_number,
                    agent=msg.agent,
                    signal=msg.signal.value,
                    confidence=msg.confidence,
                    reasoning=msg.reasoning,
                    key_factors=json.dumps(msg.key_factors, ensure_ascii=False),
                    risk_level=msg.risk_level.value if msg.risk_level else None,
                    agreement=msg.agreement,
                    disagreement_points=json.dumps(msg.disagreement_points, ensure_ascii=False),
                )
            )

        session_id = agent_session.id

    logger.info(
        "토론 세션 저장 완료",
        session_id=session_id,
        ticker=ticker,
        signal=result.final_signal.value,
        rounds=result.total_rounds,
        exit_reason=result.exit_reason.value,
    )
    return session_id


def get_recent_sessions(ticker: str, limit: Optional[int] = None) -> list[PriorSessionSummary]:
    """동일 종목의 최근 과거 토론 세션 요약 조회 (세션 간 연속성 규칙)

    새 토론을 시작하기 전 MarketContext.prior_sessions에 채우기 위해 항상 호출된다.
    과거 세션이 없으면(첫 분석) 빈 리스트를 반환한다.
    """
    limit = limit or settings.prior_sessions_limit
    summaries: list[PriorSessionSummary] = []

    with get_session() as session:
        past_sessions = (
            session.query(AgentSession)
            .filter(AgentSession.ticker == ticker)
            .order_by(AgentSession.id.desc())
            .limit(limit)
            .all()
        )

        for past in past_sessions:
            last_round = past.rounds[-1] if past.rounds else None

            signal_val = (past.final_signal or "HOLD").upper()
            signal = Signal(signal_val) if signal_val in Signal._value2member_map_ else Signal.HOLD

            reason_val = (past.exit_reason or "CLI_ERROR").upper()
            exit_reason = (
                ExitReason(reason_val)
                if reason_val in ExitReason._value2member_map_
                else ExitReason.CLI_ERROR
            )

            summaries.append(
                PriorSessionSummary(
                    session_date=str(past.session_date),
                    final_signal=signal,
                    final_confidence=past.final_confidence or 0.0,
                    exit_reason=exit_reason,
                    last_reasoning=(last_round.reasoning if last_round else "") or "",
                )
            )

    return summaries
