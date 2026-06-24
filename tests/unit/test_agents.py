"""agents 모듈 단위 테스트"""

from unittest.mock import MagicMock, patch

import pytest

from agents.local_cli_runner import extract_json_from_response
from agents.orchestrator import (
    _check_consensus,
    _detect_oscillation,
    _parse_agent_response,
    _score_to_signal,
)
from agents.protocol import AgentMessage, ExitReason, RiskLevel, Signal


def make_msg(agent: str, signal: Signal, confidence: float = 0.70, round_num: int = 1) -> AgentMessage:
    return AgentMessage(
        round_number=round_num,
        agent=agent,
        signal=signal,
        confidence=confidence,
        reasoning="test",
        risk_level=RiskLevel.MEDIUM,
    )


class TestExtractJson:
    def test_json_block(self):
        text = 'some text\n```json\n{"signal": "BUY"}\n```\n'
        result = extract_json_from_response(text)
        assert result == {"signal": "BUY"}

    def test_plain_json(self):
        text = '{"signal": "SELL", "confidence": 0.8}'
        result = extract_json_from_response(text)
        assert result["signal"] == "SELL"

    def test_invalid_returns_none(self):
        result = extract_json_from_response("not json at all")
        assert result is None


class TestParseAgentResponse:
    def test_valid_buy_response(self, mock_claude_response):
        msg = _parse_agent_response(mock_claude_response, "claude", 1)
        assert msg is not None
        assert msg.signal == Signal.BUY
        assert msg.confidence == 0.75
        assert msg.agent == "claude"
        assert len(msg.key_factors) == 3

    def test_invalid_signal_defaults_hold(self):
        raw = '{"signal": "INVALID", "confidence": 0.5, "reasoning": "test", "key_factors": []}'
        msg = _parse_agent_response(raw, "claude", 1)
        assert msg is not None
        assert msg.signal == Signal.HOLD

    def test_missing_json_returns_none(self):
        msg = _parse_agent_response("plain text no json", "claude", 1)
        assert msg is None


class TestConsensusCheck:
    def test_same_signal_high_confidence(self):
        messages = [
            make_msg("claude", Signal.BUY, 0.70),
            make_msg("codex", Signal.BUY, 0.72),
        ]
        assert _check_consensus(messages) is True

    def test_same_signal_low_confidence(self):
        messages = [
            make_msg("claude", Signal.BUY, 0.50),
            make_msg("codex", Signal.BUY, 0.55),
        ]
        assert _check_consensus(messages) is False  # avg 0.525 < 0.65

    def test_different_signals(self):
        messages = [
            make_msg("claude", Signal.BUY, 0.80),
            make_msg("codex", Signal.SELL, 0.80),
        ]
        assert _check_consensus(messages) is False

    def test_single_message(self):
        messages = [make_msg("claude", Signal.BUY, 0.80)]
        assert _check_consensus(messages) is False


class TestOscillationDetection:
    def test_buy_sell_buy_oscillation(self):
        messages = [
            make_msg("claude", Signal.BUY, round_num=1),
            make_msg("codex", Signal.SELL, round_num=2),
            make_msg("claude", Signal.BUY, round_num=3),
        ]
        assert _detect_oscillation(messages) is True

    def test_consistent_signals_no_oscillation(self):
        messages = [
            make_msg("claude", Signal.BUY, round_num=1),
            make_msg("codex", Signal.BUY, round_num=2),
            make_msg("claude", Signal.BUY, round_num=3),
        ]
        assert _detect_oscillation(messages) is False

    def test_too_few_rounds(self):
        messages = [make_msg("claude", Signal.BUY)]
        assert _detect_oscillation(messages) is False


class TestScoreToSignal:
    def test_high_positive_is_buy(self):
        assert _score_to_signal(0.5) == Signal.BUY

    def test_high_negative_is_sell(self):
        assert _score_to_signal(-0.5) == Signal.SELL

    def test_neutral_is_hold(self):
        assert _score_to_signal(0.1) == Signal.HOLD

    def test_boundary_buy(self):
        assert _score_to_signal(0.35) == Signal.BUY

    def test_boundary_sell(self):
        assert _score_to_signal(-0.35) == Signal.SELL


class TestRiskManager:
    def test_approve_buy_valid(self):
        from trading.risk_manager import RiskManager
        rm = RiskManager()
        approved, _ = rm.approve_buy(
            ticker="005930",
            quantity=10,
            price=72000,
            portfolio_value=10_000_000,
            available_cash=5_000_000,
            open_positions_count=2,
            ai_confidence=0.75,
            daily_pnl=0,
        )
        assert approved is True

    def test_reject_low_confidence(self):
        from trading.risk_manager import RiskManager
        rm = RiskManager()
        approved, reason = rm.approve_buy(
            ticker="005930",
            quantity=10,
            price=72000,
            portfolio_value=10_000_000,
            available_cash=5_000_000,
            open_positions_count=2,
            ai_confidence=0.40,  # 최소 0.65 필요
            daily_pnl=0,
        )
        assert approved is False
        assert "신뢰도" in reason

    def test_stop_loss_trigger(self):
        from trading.risk_manager import RiskManager
        rm = RiskManager()
        triggered, reason = rm.check_stop_loss("005930", avg_cost=72000, current_price=68000)
        assert triggered is True
        assert "손절" in reason

    def test_stop_loss_not_triggered(self):
        from trading.risk_manager import RiskManager
        rm = RiskManager()
        triggered, _ = rm.check_stop_loss("005930", avg_cost=72000, current_price=70000)
        assert triggered is False  # -2.8% < -5% 한도
