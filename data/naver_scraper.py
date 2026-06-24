import time
from datetime import datetime
from typing import Optional

import requests
import structlog
from bs4 import BeautifulSoup

from core.exceptions import DataFetchError

logger = structlog.get_logger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.naver.com",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def fetch_news_headlines(ticker: str, max_articles: int = 10) -> list[dict]:
    """NAVER Finance 종목 뉴스 헤드라인 수집

    Returns:
        list of {title, url, published_at, source}
    """
    url = f"https://finance.naver.com/item/news_news.naver?code={ticker}&page=1"
    try:
        response = requests.get(url, headers=_HEADERS, timeout=10)
        response.raise_for_status()
        response.encoding = "euc-kr"

        soup = BeautifulSoup(response.text, "lxml")
        articles = []

        rows = soup.select("table.type5 tr")
        for row in rows:
            title_tag = row.select_one("td.title a")
            date_tag = row.select_one("td.date")
            source_tag = row.select_one("td.info")

            if not title_tag or not date_tag:
                continue

            title = title_tag.get_text(strip=True)
            href = title_tag.get("href", "")
            article_url = f"https://finance.naver.com{href}" if href.startswith("/") else href

            date_text = date_tag.get_text(strip=True)
            published_at = _parse_naver_date(date_text)
            source = source_tag.get_text(strip=True) if source_tag else "naver"

            if title:
                articles.append({
                    "title": title,
                    "url": article_url,
                    "published_at": published_at,
                    "source": source,
                })

            if len(articles) >= max_articles:
                break

        logger.info("뉴스 수집 완료", ticker=ticker, count=len(articles))
        return articles

    except requests.RequestException as e:
        logger.error("뉴스 수집 실패", ticker=ticker, error=str(e))
        raise DataFetchError(f"뉴스 수집 실패: ticker={ticker}") from e


def fetch_article_body(url: str) -> Optional[str]:
    """뉴스 본문 수집 (감정 분석용)"""
    try:
        time.sleep(0.5)  # 요청 간격 준수
        response = requests.get(url, headers=_HEADERS, timeout=10)
        response.raise_for_status()
        response.encoding = "euc-kr"

        soup = BeautifulSoup(response.text, "lxml")
        # NAVER 뉴스 본문 영역
        body_tag = soup.select_one("div#news_read") or soup.select_one("div.articleCont")
        if not body_tag:
            return None

        text = body_tag.get_text(separator=" ", strip=True)
        return text[:2000]  # 최대 2000자

    except Exception as e:
        logger.warning("본문 수집 실패", url=url, error=str(e))
        return None


def fetch_all_top10_news(tickers: list[str], max_per_ticker: int = 5) -> dict[str, list[dict]]:
    """상위 10개 종목 뉴스 일괄 수집"""
    result: dict[str, list[dict]] = {}
    for ticker in tickers:
        try:
            result[ticker] = fetch_news_headlines(ticker, max_per_ticker)
            time.sleep(1.0)  # 크롤링 간격
        except DataFetchError:
            result[ticker] = []
    return result


def _parse_naver_date(date_text: str) -> datetime:
    """NAVER 날짜 텍스트 파싱 (예: '2024.01.15 09:30')"""
    try:
        return datetime.strptime(date_text.strip(), "%Y.%m.%d %H:%M")
    except ValueError:
        try:
            return datetime.strptime(date_text.strip(), "%Y.%m.%d")
        except ValueError:
            return datetime.now()
