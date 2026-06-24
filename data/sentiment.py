"""뉴스 텍스트 감성 점수화 (사전 기반)

외부 모델(FinBERT 등) 의존성 추가 없이, 한국어 금융 뉴스에서 흔히 쓰이는
긍정/부정 키워드 빈도를 기반으로 -1.0~+1.0 사이의 감성 점수를 산출한다.
"""

from __future__ import annotations

_POSITIVE_KEYWORDS = [
    "상승",
    "급등",
    "호조",
    "개선",
    "흑자",
    "수주",
    "성장",
    "돌파",
    "신고가",
    "목표가 상향",
    "최대 실적",
    "어닝 서프라이즈",
    "강세",
    "확대",
    "회복",
]

_NEGATIVE_KEYWORDS = [
    "하락",
    "급락",
    "악화",
    "적자",
    "감소",
    "부진",
    "경고",
    "우려",
    "신저가",
    "목표가 하향",
    "어닝 쇼크",
    "약세",
    "축소",
    "리스크",
    "소송",
    "제재",
]


def score_text_sentiment(text: str | None) -> float | None:
    """텍스트 내 긍정/부정 키워드 빈도 기반 감성 점수화.

    Returns:
        -1.0(매우 부정)~+1.0(매우 긍정). 키워드가 전혀 없으면 0.0.
        text가 비어있으면 None.
    """
    if not text or not text.strip():
        return None

    pos_count = sum(text.count(kw) for kw in _POSITIVE_KEYWORDS)
    neg_count = sum(text.count(kw) for kw in _NEGATIVE_KEYWORDS)
    total = pos_count + neg_count
    if total == 0:
        return 0.0

    score = (pos_count - neg_count) / total
    return round(max(-1.0, min(1.0, score)), 4)


def aggregate_sentiment(scores: list[float | None]) -> float | None:
    """여러 기사의 감성 점수를 평균. 유효한 점수가 하나도 없으면 None."""
    valid = [s for s in scores if s is not None]
    if not valid:
        return None
    return round(sum(valid) / len(valid), 4)
