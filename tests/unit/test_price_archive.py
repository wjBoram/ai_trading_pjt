"""scripts/collect_price_archive.py, scripts/load_price_archive.py 단위 테스트"""

import sys
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
import collect_price_archive as archive_script  # noqa: E402
import load_price_archive as load_script  # noqa: E402

from core.models import OHLCVDaily


def _fake_ohlcv(ticker: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": [ticker, ticker],
            "date": [date(2026, 1, 5), date(2026, 1, 6)],
            "open": [100, 101],
            "high": [110, 111],
            "low": [90, 95],
            "close": [105, 106],
            "volume": [1000, 1100],
        }
    )


@pytest.fixture
def patched_get_session(monkeypatch, test_engine):
    """data_manager.get_session을 테스트용 in-memory 엔진으로 교체"""
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

    monkeypatch.setattr("data.data_manager.get_session", _get_session)
    return session_factory


@pytest.fixture
def isolated_archive_dir(monkeypatch, tmp_path):
    """ARCHIVE_DIR/ARCHIVE_INDEX를 임시 디렉터리로 격리 (실제 data_store 건드리지 않음)"""
    archive_dir = tmp_path / "price_archive"
    monkeypatch.setattr(archive_script, "ARCHIVE_DIR", archive_dir)
    monkeypatch.setattr(archive_script, "ARCHIVE_INDEX", archive_dir / "ARCHIVE_INDEX.md")
    monkeypatch.setattr(load_script, "ARCHIVE_DIR", archive_dir)
    return archive_dir


class TestCollectOne:
    def test_ticker_leading_zero_preserved_in_json(
        self, isolated_archive_dir, patched_get_session, monkeypatch
    ):
        monkeypatch.setitem(
            archive_script._FETCHERS, "daily", lambda ticker, start, end: _fake_ohlcv(ticker)
        )

        filepath = archive_script.collect_one("005930", "daily", 30)

        df = pd.read_json(filepath, dtype={"ticker": str})
        assert (df["ticker"] == "005930").all()

    def test_daily_upserts_into_db(self, isolated_archive_dir, patched_get_session, monkeypatch):
        monkeypatch.setitem(
            archive_script._FETCHERS, "daily", lambda ticker, start, end: _fake_ohlcv(ticker)
        )

        archive_script.collect_one("005930", "daily", 30)

        session = patched_get_session()
        count = session.query(OHLCVDaily).filter(OHLCVDaily.ticker == "005930").count()
        session.close()
        assert count == 2

    def test_non_daily_timeframe_does_not_touch_db(
        self, isolated_archive_dir, patched_get_session, monkeypatch
    ):
        # 다른 테스트와 공유하는 in-memory DB에 영향받지 않도록 전용 ticker 사용
        ticker = "TST900"
        monkeypatch.setitem(
            archive_script._FETCHERS, "monthly", lambda t, start, end: _fake_ohlcv(t)
        )

        archive_script.collect_one(ticker, "monthly", 365)

        session = patched_get_session()
        count = session.query(OHLCVDaily).filter(OHLCVDaily.ticker == ticker).count()
        session.close()
        assert count == 0

    def test_updates_archive_index(self, isolated_archive_dir, patched_get_session, monkeypatch):
        monkeypatch.setitem(
            archive_script._FETCHERS, "weekly", lambda ticker, start, end: _fake_ohlcv(ticker)
        )

        archive_script.collect_one("005930", "weekly", 365)

        index_text = archive_script.ARCHIVE_INDEX.read_text(encoding="utf-8")
        assert "005930" in index_text
        assert "weekly" in index_text


class TestLoadOne:
    def test_round_trip_preserves_ticker_and_restores_db(
        self, isolated_archive_dir, patched_get_session, monkeypatch
    ):
        monkeypatch.setitem(
            archive_script._FETCHERS, "daily", lambda ticker, start, end: _fake_ohlcv(ticker)
        )
        archive_script.collect_one("005930", "daily", 30)

        # DB를 비워서(예: 새 환경) 재적재가 실제로 데이터를 복원하는지 확인
        session = patched_get_session()
        session.query(OHLCVDaily).filter(OHLCVDaily.ticker == "005930").delete()
        session.commit()
        assert session.query(OHLCVDaily).filter(OHLCVDaily.ticker == "005930").count() == 0
        session.close()

        rows = load_script.load_one("005930")

        session = patched_get_session()
        count = session.query(OHLCVDaily).filter(OHLCVDaily.ticker == "005930").count()
        session.close()
        assert rows == 2
        assert count == 2

    def test_missing_archive_returns_zero(self, isolated_archive_dir, patched_get_session):
        assert load_script.load_one("999999") == 0
