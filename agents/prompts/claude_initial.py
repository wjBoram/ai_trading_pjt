"""Round 1: Claude 초기 분석 프롬프트"""

from agents.protocol import MarketContext
from agents.prompts.context_builder import build_market_context_text

_SYSTEM = """당신은 한국 주식시장(KOSPI/KOSDAQ) 전문 퀀트 애널리스트입니다.
주어진 기술적 지표와 뉴스 데이터를 바탕으로 다음 거래일의 매수/매도/홀드 신호를 분석합니다.
반드시 JSON 형식으로 응답하세요."""

_TEMPLATE = """{system}

{market_context}

[분석 지시사항]
위 데이터를 분석하여 {ticker}({company})의 내일(다음 거래일) 매매 신호를 판단하세요.

다음 기준으로 신호를 결정하세요:
- BUY: 상승 가능성이 높아 매수 적합 (다음 거래일 +1% 이상 예상)
- SELL: 하락 가능성이 높아 보유 중이라면 매도 적합 (다음 거래일 -1% 이상 예상)
- HOLD: 방향성 불명확하거나 현재 포지션 유지 적합

반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
```json
{{
  "signal": "BUY" | "SELL" | "HOLD",
  "confidence": 0.0~1.0,
  "reasoning": "200자 이내 근거 (구체적 지표 수치 인용)",
  "key_factors": ["핵심 요인 1", "핵심 요인 2", "핵심 요인 3"],
  "risk_level": "low" | "medium" | "high"
}}
```"""


def build_prompt(ctx: MarketContext) -> str:
    market_text = build_market_context_text(ctx)
    return _TEMPLATE.format(
        system=_SYSTEM,
        market_context=market_text,
        ticker=ctx.ticker,
        company=ctx.company_name,
    )
