"""통합 데이터 수집 오케스트레이터"""

from datetime import date, timedelta

import pandas as pd
import structlog

from core.database import get_session
from core.exceptions import DataFetchError
from core.models import NewsArticle, OHLCVDaily, Stock
from data.naver_scraper import fetch_all_top10_news, fetch_article_body
from data.pykrx_client import TOP_10_TICKERS, fetch_all_top10_ohlcv, get_top_10_tickers
from data.sentiment import score_text_sentiment

logger = structlog.get_logger(__name__)


def initialize_stocks() -> None:
    """종목 마스터 데이터 초기 적재"""
    with get_session() as session:
        for ticker, name in get_top_10_tickers().items():
            existing = session.get(Stock, ticker)
            if not existing:
                session.add(Stock(ticker=ticker, name=name, market="KOSPI", is_active=True))
        logger.info("종목 마스터 초기화 완료", count=len(TOP_10_TICKERS))


def backfill_ohlcv(days: int = 730) -> None:
    """2년치 OHLCV 백필"""
    end = date.today()
    start = end - timedelta(days=days)
    logger.info("OHLCV 백필 시작", start=str(start), end=str(end))

    data = fetch_all_top10_ohlcv(start=start, end=end)

    for ticker, df in data.items():
        upsert_ohlcv(ticker, df)

    logger.info("OHLCV 백필 완료", tickers=len(data))


def refresh_daily_ohlcv() -> None:
    """당일 + 최근 5일 OHLCV 갱신"""
    end = date.today()
    start = end - timedelta(days=5)

    data = fetch_all_top10_ohlcv(start=start, end=end)
    for ticker, df in data.items():
        upsert_ohlcv(ticker, df)

    logger.info("일일 OHLCV 갱신 완료", tickers=len(data))


def refresh_news() -> None:
    """상위 10개 종목 뉴스 갱신 (신규 기사는 본문 수집 + 감성 점수화)"""
    tickers = list(get_top_10_tickers().keys())
    news_by_ticker = fetch_all_top10_news(tickers, max_per_ticker=5)

    with get_session() as session:
        total = 0
        for ticker, articles in news_by_ticker.items():
            for article in articles:
                existing = (
                    session.query(NewsArticle)
                    .filter(
                        NewsArticle.ticker == ticker,
                        NewsArticle.title == article["title"],
                    )
                    .first()
                )
                if not existing:
                    body = fetch_article_body(article["url"])
                    sentiment_score = score_text_sentiment(body or article["title"])
                    session.add(
                        NewsArticle(
                            ticker=ticker,
                            title=article["title"],
                            body=body,
                            source=article.get("source", "naver"),
                            published_at=article["published_at"],
                            sentiment_score=sentiment_score,
                        )
                    )
                    total += 1

    logger.info("뉴스 갱신 완료", new_articles=total)


def get_recent_ohlcv(ticker: str, days: int = 60) -> pd.DataFrame:
    """DB에서 최근 N일 OHLCV 조회"""
    cutoff = date.today() - timedelta(days=days)
    with get_session() as session:
        records = (
            session.query(OHLCVDaily)
            .filter(OHLCVDaily.ticker == ticker, OHLCVDaily.date >= cutoff)
            .order_by(OHLCVDaily.date)
            .all()
        )
        if not records:
            return pd.DataFrame()

        data = [
            {
                "date": r.date,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in records
        ]
        return pd.DataFrame(data)


def get_recent_news(ticker: str, max_articles: int = 10) -> list[dict]:
    """DB에서 최근 뉴스 조회"""
    with get_session() as session:
        records = (
            session.query(NewsArticle)
            .filter(NewsArticle.ticker == ticker)
            .order_by(NewsArticle.published_at.desc())
            .limit(max_articles)
            .all()
        )
        return [
            {
                "title": r.title,
                "published_at": r.published_at,
                "sentiment_score": r.sentiment_score,
            }
            for r in records
        ]


def upsert_ohlcv(ticker: str, df: pd.DataFrame) -> None:
    """OHLCV INSERT OR REPLACE"""
    with get_session() as session:
        for _, row in df.iterrows():
            existing = (
                session.query(OHLCVDaily)
                .filter(OHLCVDaily.ticker == ticker, OHLCVDaily.date == row["date"])
                .first()
            )
            if existing:
                existing.open = row["open"]
                existing.high = row["high"]
                existing.low = row["low"]
                existing.close = row["close"]
                existing.volume = row["volume"]
            else:
                session.add(
                    OHLCVDaily(
                        ticker=ticker,
                        date=row["date"],
                        open=row["open"],
                        high=row["high"],
                        low=row["low"],
                        close=row["close"],
                        volume=row["volume"],
                    )
                )
