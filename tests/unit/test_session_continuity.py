"""AI 토론 세션 간 연속성(get_recent_sessions, build_prior_sessions_text) 단위 테스트"""

from contextlib import contextmanager
from datetime import date

import pytest
from sqlalchemy.orm import sessionmaker

from agents.prompts.context_builder import build_prior_sessions_text
from agents.protocol import ExitReason, PriorSessionSummary, Signal
from core.models import AgentRound, AgentSession


@pytest.fixture
def patched_get_session(monkeypatch, test_engine):
    """agents.orchestrator.get_session을 테스트용 in-memory 엔진으로 교체하고
    세션 팩토리를 반환 (테스트 데이터 삽입용)."""
    session_factory = sessionmaker(bind=test_engine)

    @contextmanager
    def _get_session():
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr("agents.orchestrator.get_session", _get_session)
    return session_factory


def _insert_session(
    session_factory,
    ticker: str,
    session_date: date,
    signal: str,
    confidence: float,
    exit_reason: str,
    reasoning: str,
) -> None:
    session = session_factory()
    agent_session = AgentSession(
        ticker=ticker,
        session_date=session_date,
        total_rounds=1,
        final_signal=signal,
        final_confidence=confidence,
        weighted_score=0.5,
        exit_reason=exit_reason,
        execute_trade=False,
    )
    session.add(agent_session)
    session.flush()
    session.add(
        AgentRound(
            session_id=agent_session.id,
            round_number=1,
            agent="claude",
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
        )
    )
    session.commit()
    session.close()


class TestGetRecentSessions:
    def test_returns_empty_list_for_unknown_ticker(self, patched_get_session):
        from agents.orchestrator import get_recent_sessions

        assert get_recent_sessions("NOPE001") == []

    def test_returns_recent_sessions_newest_first(self, patched_get_session):
        from agents.orchestrator import get_recent_sessions

        ticker = "TST001"
        _insert_session(
            patched_get_session, ticker, date(2024, 1, 1), "BUY", 0.7, "CONSENSUS", "1일차 근거"
        )
        _insert_session(
            patched_get_session, ticker, date(2024, 1, 2), "SELL", 0.6, "MAX_ROUNDS", "2일차 근거"
        )

        result = get_recent_sessions(ticker, limit=5)

        assert len(result) == 2
        assert result[0].session_date == "2024-01-02"
        assert result[0].final_signal == Signal.SELL
        assert result[0].last_reasoning == "2일차 근거"
        assert result[1].session_date == "2024-01-01"

    def test_respects_limit(self, patched_get_session):
        from agents.orchestrator import get_recent_sessions

        ticker = "TST002"
        for i in range(5):
            _insert_session(
                patched_get_session,
                ticker,
                date(2024, 1, i + 1),
                "HOLD",
                0.5,
                "CONSENSUS",
                f"{i}일차",
            )

        result = get_recent_sessions(ticker, limit=2)
        assert len(result) == 2

    def test_session_with_no_rounds_has_empty_reasoning(self, patched_get_session):
        from agents.orchestrator import get_recent_sessions

        ticker = "TST003"
        session = patched_get_session()
        session.add(
            AgentSession(
                ticker=ticker,
                session_date=date(2024, 1, 1),
                total_rounds=0,
                final_signal="HOLD",
                final_confidence=0.0,
                weighted_score=0.0,
                exit_reason="CLI_ERROR",
                execute_trade=False,
            )
        )
        session.commit()
        session.close()

        result = get_recent_sessions(ticker)
        assert len(result) == 1
        assert result[0].last_reasoning == ""
        assert result[0].exit_reason == ExitReason.CLI_ERROR


class TestBuildPriorSessionsText:
    def test_empty_list_returns_first_analysis_message(self):
        assert "첫 분석" in build_prior_sessions_text([])

    def test_renders_session_summary(self):
        summaries = [
            PriorSessionSummary(
                session_date="2024-01-02",
                final_signal=Signal.BUY,
                final_confidence=0.75,
                exit_reason=ExitReason.CONSENSUS,
                last_reasoning="RSI 과매도 구간 탈출",
            )
        ]
        text = build_prior_sessions_text(summaries)
        assert "2024-01-02" in text
        assert "BUY" in text
        assert "75%" in text
        assert "RSI 과매도 구간 탈출" in text

    def test_truncates_long_reasoning(self):
        summaries = [
            PriorSessionSummary(
                session_date="2024-01-02",
                final_signal=Signal.HOLD,
                final_confidence=0.5,
                exit_reason=ExitReason.MAX_ROUNDS,
                last_reasoning="가" * 200,
            )
        ]
        text = build_prior_sessions_text(summaries)
        assert "..." in text
