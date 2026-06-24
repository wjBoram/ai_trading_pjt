"""Round 2: Codex 검토 프롬프트"""

from agents.protocol import AgentMessage, MarketContext
from agents.prompts.context_builder import build_history_text, build_market_context_text

_SYSTEM = """당신은 한국 주식시장 전문 리스크 애널리스트입니다.
다른 AI 애널리스트(Claude)의 분석을 독립적으로 검토하고 비판적으로 평가합니다.
반드시 JSON 형식으로 응답하세요."""

_TEMPLATE = """{system}

{market_context}

[선행 분석 (Claude Round 1)]
{prior_analysis}

[검토 지시사항]
위 시장 데이터를 독립적으로 분석한 후, Claude의 분석을 비판적으로 검토하세요.

1. 먼저 데이터를 독립적으로 평가하여 자신의 신호를 결정하세요.
2. Claude의 분석에서 동의하는 부분과 동의하지 않는 부분을 명확히 구분하세요.
3. 특히 Claude가 놓친 리스크나 과장된 긍정/부정 요인을 지적하세요.

반드시 아래 JSON 형식으로만 응답하세요:
```json
{{
  "signal": "BUY" | "SELL" | "HOLD",
  "confidence": 0.0~1.0,
  "reasoning": "200자 이내 독립 분석 근거",
  "key_factors": ["핵심 요인 1", "핵심 요인 2", "핵심 요인 3"],
  "risk_level": "low" | "medium" | "high",
  "agreement_with_prior": true | false,
  "disagreement_points": ["반박 포인트 1", "반박 포인트 2"]
}}
```
(동의하는 경우 disagreement_points는 빈 배열 [])"""


def build_prompt(ctx: MarketContext, prior_messages: list[AgentMessage]) -> str:
    market_text = build_market_context_text(ctx)
    history_text = build_history_text(prior_messages)
    return _TEMPLATE.format(
        system=_SYSTEM,
        market_context=market_text,
        prior_analysis=history_text,
    )
