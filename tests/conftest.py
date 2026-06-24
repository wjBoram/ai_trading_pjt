"""공통 테스트 픽스처"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.models import Base


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    session = sessionmaker(bind=test_engine)()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_ohlcv_data():
    """테스트용 OHLCV 데이터 (30일)"""
    import pandas as pd
    from datetime import date, timedelta

    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(30)]
    closes = [70000 + i * 100 + (i % 3 - 1) * 200 for i in range(30)]

    return pd.DataFrame({
        "date": dates,
        "open": [c - 300 for c in closes],
        "high": [c + 500 for c in closes],
        "low": [c - 500 for c in closes],
        "close": closes,
        "volume": [1_000_000 + i * 10000 for i in range(30)],
    })


@pytest.fixture
def sample_market_context():
    """테스트용 MarketContext"""
    from agents.protocol import MarketContext

    return MarketContext(
        ticker="005930",
        company_name="삼성전자",
        current_price=72000,
        day_change_pct=1.5,
        ohlcv_20d=[
            {"date": "2024-01-15", "open": 71000, "high": 72500, "low": 70800, "close": 72000, "volume": 1500000}
        ],
        indicators={"rsi": 55.0, "macd": 120.0, "macd_signal": 100.0, "macd_hist": 20.0,
                    "volume_ratio": 1.2, "return_1d": 0.015, "atr_pct": 0.015},
        news_headlines=["삼성전자 실적 호조", "반도체 업황 회복"],
        volume_ratio=1.2,
        market_date="2024-01-15",
    )


@pytest.fixture
def mock_claude_response():
    return """{
  "signal": "BUY",
  "confidence": 0.75,
  "reasoning": "RSI 55로 과매수 아님, MACD 히스토그램 양전환, 거래량 비율 1.2x로 증가 추세",
  "key_factors": ["MACD 골든크로스", "거래량 증가", "실적 호조 뉴스"],
  "risk_level": "medium"
}"""


@pytest.fixture
def mock_codex_response():
    return """{
  "signal": "BUY",
  "confidence": 0.70,
  "reasoning": "Claude의 기술적 분석에 동의. 볼린저밴드 중간선 위에 있어 상승 모멘텀 확인",
  "key_factors": ["볼린저밴드 중단선 돌파", "MACD 양전환"],
  "risk_level": "medium",
  "agreement_with_prior": true,
  "disagreement_points": []
}"""
