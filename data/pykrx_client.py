from datetime import date, timedelta
from typing import Optional

import pandas as pd
import structlog

from core.exceptions import DataFetchError

logger = structlog.get_logger(__name__)

# KOSPI 시총 상위 10개 종목 (주기적으로 갱신 필요)
TOP_10_TICKERS: dict[str, str] = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "373220": "LG에너지솔루션",
    "207940": "삼성바이오로직스",
    "005380": "현대차",
    "000270": "기아",
    "068270": "셀트리온",
    "105560": "KB금융",
    "055550": "신한지주",
    "028260": "삼성물산",
}


def get_top_10_tickers() -> dict[str, str]:
    """상위 10개 종목 반환 (시총 기준 하드코딩, 주 1회 갱신 권장)"""
    return TOP_10_TICKERS


def _normalize_ohlcv_df(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """pykrx 원본 OHLCV DataFrame(한글 컬럼·날짜 인덱스)을 표준 컬럼으로 정규화"""
    df = df.rename(
        columns={"시가": "open", "고가": "high", "저가": "low", "종가": "close", "거래량": "volume"}
    )
    df.index.name = "date"
    df = df.reset_index()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["ticker"] = ticker
    df = df[["ticker", "date", "open", "high", "low", "close", "volume"]]
    return df.dropna()


def _fetch_ohlcv_with_freq(
    ticker: str,
    freq: str,
    start: Optional[date],
    end: Optional[date],
    default_days: int,
) -> pd.DataFrame:
    """pykrx freq 파라미터(d/m/y)로 OHLCV 수집 후 표준 컬럼으로 정규화"""
    try:
        from pykrx import stock as pykrx_stock

        end = end or date.today()
        start = start or (end - timedelta(days=default_days))

        start_str = start.strftime("%Y%m%d")
        end_str = end.strftime("%Y%m%d")

        df = pykrx_stock.get_market_ohlcv(start_str, end_str, ticker, freq=freq)

        if df is None or df.empty:
            raise DataFetchError(f"OHLCV 데이터 없음: {ticker} freq={freq}")

        df = _normalize_ohlcv_df(df, ticker)

        logger.info(
            "OHLCV 수집 완료", ticker=ticker, freq=freq, rows=len(df), start=start_str, end=end_str
        )
        return df

    except DataFetchError:
        raise
    except Exception as e:
        logger.error("OHLCV 수집 실패", ticker=ticker, freq=freq, error=str(e))
        raise DataFetchError(f"ticker={ticker} freq={freq}") from e


def fetch_ohlcv(
    ticker: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> pd.DataFrame:
    """pykrx로 일봉 OHLCV 수집

    Returns:
        columns: date, open, high, low, close, volume
    """
    return _fetch_ohlcv_with_freq(ticker, "d", start, end, default_days=365 * 2)


def fetch_ohlcv_monthly(
    ticker: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> pd.DataFrame:
    """pykrx로 월봉 OHLCV 수집 (freq='m')"""
    return _fetch_ohlcv_with_freq(ticker, "m", start, end, default_days=365)


def fetch_ohlcv_yearly(
    ticker: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> pd.DataFrame:
    """pykrx로 연봉 OHLCV 수집 (freq='y')"""
    return _fetch_ohlcv_with_freq(ticker, "y", start, end, default_days=365)


def fetch_ohlcv_weekly(
    ticker: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> pd.DataFrame:
    """일봉 OHLCV를 주봉(금요일 마감 기준)으로 파생 집계

    pykrx는 주봉 freq를 지원하지 않으므로(d/m/y만 가능) 일봉을 resample해서 만든다.
    """
    daily = fetch_ohlcv(ticker, start, end)
    if daily.empty:
        return daily

    indexed = daily.set_index(pd.to_datetime(daily["date"]))
    weekly = indexed.resample("W-FRI").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    weekly = weekly.dropna()
    weekly.index.name = "date"
    weekly = weekly.reset_index()
    weekly["date"] = weekly["date"].dt.date
    weekly["ticker"] = ticker
    weekly = weekly[["ticker", "date", "open", "high", "low", "close", "volume"]]

    logger.info("OHLCV 주봉 파생 완료", ticker=ticker, rows=len(weekly))
    return weekly


def fetch_all_top10_ohlcv(
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> dict[str, pd.DataFrame]:
    """상위 10개 종목 OHLCV 일괄 수집"""
    result: dict[str, pd.DataFrame] = {}
    for ticker in get_top_10_tickers():
        try:
            result[ticker] = fetch_ohlcv(ticker, start, end)
        except DataFetchError as e:
            logger.warning("종목 수집 건너뜀", ticker=ticker, error=str(e))
    return result


def get_current_price(ticker: str) -> Optional[float]:
    """현재가 조회 (pykrx, 장 마감 후에는 당일 종가)"""
    try:
        from pykrx import stock as pykrx_stock

        today = date.today().strftime("%Y%m%d")
        df = pykrx_stock.get_market_ohlcv(today, today, ticker)
        if df is None or df.empty:
            return None
        return float(df["종가"].iloc[-1])
    except Exception as e:
        logger.warning("현재가 조회 실패", ticker=ticker, error=str(e))
        return None
