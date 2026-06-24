"""시간단위별(일/주/월/연봉) 가격 데이터를 종목 하나씩 수집해 JSON 아카이브로 저장

일봉은 기존 DB(OHLCVDaily)도 함께 갱신한다. 주/월/연봉은 전용 DB 테이블이 아직 없어
JSON 파일로만 보관한다(추후 테이블이 추가되면 재적재 가능하도록 동일 구조로 저장).

사용법:
    python scripts/collect_price_archive.py --ticker 005930 --timeframe daily
    python scripts/collect_price_archive.py --ticker 005930 --timeframe weekly --days 730
    python scripts/collect_price_archive.py --ticker all --timeframe monthly
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.logging_config import setup_logging
from config.settings import settings
from core.exceptions import DataFetchError
from data.pykrx_client import (
    TOP_10_TICKERS,
    fetch_ohlcv,
    fetch_ohlcv_monthly,
    fetch_ohlcv_weekly,
    fetch_ohlcv_yearly,
)

_FETCHERS = {
    "daily": fetch_ohlcv,
    "weekly": fetch_ohlcv_weekly,
    "monthly": fetch_ohlcv_monthly,
    "yearly": fetch_ohlcv_yearly,
}

ARCHIVE_DIR = Path(__file__).parent.parent / "data_store" / "price_archive"
ARCHIVE_INDEX = ARCHIVE_DIR / "ARCHIVE_INDEX.md"


def collect_one(ticker: str, timeframe: str, days: int) -> Path:
    """종목 1개 + 시간단위 1개를 수집해 JSON 아카이브로 저장 (일봉은 DB도 갱신)"""
    end = date.today()
    start = end - timedelta(days=days)

    df = _FETCHERS[timeframe](ticker, start, end)

    ticker_dir = ARCHIVE_DIR / ticker
    ticker_dir.mkdir(parents=True, exist_ok=True)
    filepath = ticker_dir / f"{timeframe}.json"

    records = df.copy()
    records["date"] = records["date"].astype(str)
    filepath.write_text(
        records.to_json(orient="records", force_ascii=False, indent=2), encoding="utf-8"
    )

    if timeframe == "daily":
        from data.data_manager import upsert_ohlcv

        upsert_ohlcv(ticker, df)

    _update_archive_index(ticker, timeframe, len(df), start, end)
    return filepath


def _update_archive_index(ticker: str, timeframe: str, rows: int, start: date, end: date) -> None:
    """ARCHIVE_INDEX.md에 수집 결과 한 줄 추가"""
    if not ARCHIVE_INDEX.exists():
        ARCHIVE_INDEX.write_text(
            "# 가격 아카이브 인덱스\n\n"
            "`scripts/collect_price_archive.py`로 수집된 JSON 파일 기록.\n"
            "일봉은 `OHLCVDaily` DB와 함께 갱신됨. 주/월/연봉은 파일로만 보관(전용 테이블 없음).\n\n"
            "| 종목 | 시간단위 | 기간 | 행수 | 갱신시각 |\n"
            "|------|---------|------|------|----------|\n",
            encoding="utf-8",
        )

    name = TOP_10_TICKERS.get(ticker, ticker)
    row = (
        f"| {ticker} ({name}) | {timeframe} | {start} ~ {end} | {rows} | "
        f"{datetime.now():%Y-%m-%d %H:%M:%S} |\n"
    )
    with ARCHIVE_INDEX.open("a", encoding="utf-8") as f:
        f.write(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="시간단위별 가격 데이터 수집 (JSON 아카이브)")
    parser.add_argument("--ticker", required=True, help="종목코드(예: 005930) 또는 'all'")
    parser.add_argument(
        "--timeframe",
        required=True,
        choices=list(_FETCHERS.keys()),
        help="daily/weekly/monthly/yearly",
    )
    parser.add_argument("--days", type=int, default=365, help="조회 기간(일), 기본 365(1년)")
    args = parser.parse_args()

    setup_logging(settings.log_level)

    tickers = list(TOP_10_TICKERS.keys()) if args.ticker == "all" else [args.ticker]

    for ticker in tickers:
        try:
            filepath = collect_one(ticker, args.timeframe, args.days)
            print(f"{ticker} {args.timeframe}: {filepath}")
        except DataFetchError as e:
            print(f"{ticker} {args.timeframe} 수집 실패: {e}")


if __name__ == "__main__":
    main()
