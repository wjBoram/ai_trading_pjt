"""JSON 가격 아카이브를 읽어 DB(OHLCVDaily)를 재구성

DB가 손상되거나 새 환경으로 옮길 때, data_store/price_archive/{ticker}/daily.json을
다시 읽어 OHLCVDaily 테이블을 복원한다. 현재는 일봉만 지원한다 — 주/월/연봉은 전용
DB 테이블이 아직 없어 파일로만 보관되며(scripts/collect_price_archive.py 참고), 해당
테이블이 추가되는 시점에 이 스크립트도 함께 확장한다.

사용법:
    python scripts/load_price_archive.py --ticker 005930
    python scripts/load_price_archive.py --ticker all
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from config.logging_config import setup_logging
from config.settings import settings
from core.database import init_db
from data.data_manager import upsert_ohlcv
from data.pykrx_client import TOP_10_TICKERS

ARCHIVE_DIR = Path(__file__).parent.parent / "data_store" / "price_archive"


def load_one(ticker: str) -> int:
    """종목 1개의 daily.json을 읽어 OHLCVDaily에 재적재. 적재된 행수 반환."""
    filepath = ARCHIVE_DIR / ticker / "daily.json"
    if not filepath.exists():
        print(f"{ticker}: 아카이브 없음 ({filepath})")
        return 0

    # ticker는 "005930"처럼 앞자리 0이 있어 dtype 명시 없이는 숫자로 잘못 추론됨(0 손실)
    df = pd.read_json(filepath, dtype={"ticker": str})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    upsert_ohlcv(ticker, df)
    return len(df)


def main() -> None:
    parser = argparse.ArgumentParser(description="JSON 가격 아카이브를 DB로 재적재 (일봉만)")
    parser.add_argument("--ticker", required=True, help="종목코드(예: 005930) 또는 'all'")
    args = parser.parse_args()

    setup_logging(settings.log_level)
    init_db()

    tickers = list(TOP_10_TICKERS.keys()) if args.ticker == "all" else [args.ticker]

    for ticker in tickers:
        rows = load_one(ticker)
        if rows:
            print(f"{ticker}: {rows}행 재적재 완료")


if __name__ == "__main__":
    main()
