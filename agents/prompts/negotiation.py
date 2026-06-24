"""Round 3+: 협상 라운드 프롬프트 (claude/codex 공용)"""

from agents.protocol import AgentMessage, MarketContext
from agents.prompts.context_builder import build_history_text, build_market_context_text

_CLAUDE_REBUTTAL = """당신은 한국 주식시장 전문 퀀트 애널리스트 Claude입니다.
Codex 애널리스트의 비판을 받았습니다. 아래 전체 토론 히스토리를 검토하고,
Codex의 반박 포인트에 대해 구체적으로 답변하며 최종 입장을 정리하세요.
반드시 JSON 형식으로 응답하세요."""

_CODEX_REBUTTAL = """당신은 한국 주식시장 전문 리스크 애널리스트 Codex입니다.
Claude 애널리스트의 반론을 받았습니다. 아래 전체 토론 히스토리를 검토하고,
Claude의 새로운 주장을 평가하며 자신의 최종 입장을 정리하세요.
반드시 JSON 형식으로 응답하세요."""

_TEMPLATE = """{system}

{market_context}

[전체 토론 히스토리]
{history}

[라운드 {round_number} 지시사항]
위 토론 내용을 바탕으로 상대방의 주장을 수용하거나 반박하며 최종 입장을 확정하세요.
- 상대방의 논거가 타당하다면 신호를 변경할 수 있습니다.
- 자신의 분석이 더 타당하다면 신호를 유지하되 근거를 보강하세요.
- 신호 변경 여부(signal_changed)를 반드시 명시하세요.

반드시 아래 JSON 형식으로만 응답하세요:
```json
{{
  "signal": "BUY" | "SELL" | "HOLD",
  "confidence": 0.0~1.0,
  "reasoning": "200자 이내 최종 입장 근거",
  "key_factors": ["핵심 요인 1", "핵심 요인 2"],
  "risk_level": "low" | "medium" | "high",
  "agreement_with_prior": true | false,
  "disagreement_points": ["여전히 동의 못 하는 포인트"],
  "signal_changed": true | false
}}
```"""


def build_prompt(
    ctx: MarketContext,
    messages: list[AgentMessage],
    current_agent: str,
    round_number: int,
) -> str:
    system = _CLAUDE_REBUTTAL if current_agent == "claude" else _CODEX_REBUTTAL
    market_text = build_market_context_text(ctx)
    history_text = build_history_text(messages)

    return _TEMPLATE.format(
        system=system,
        market_context=market_text,
        history=history_text,
        round_number=round_number,
    )
