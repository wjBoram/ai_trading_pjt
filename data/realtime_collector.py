"""실시간·배치·수기 데이터 갱신 + 즉시 AI 분석 트리거"""

import threading
from datetime import date, datetime, timedelta
from typing import Callable, Optional

import structlog

from core.database import get_session
from core.exceptions import DataFetchError
from core.models import OHLCVDaily
from data.pykrx_client import TOP_10_TICKERS, get_current_price

logger = structlog.get_logger(__name__)

# 분봉·시간봉 지원 추가
CANDLE_TYPES = {
    "1d": "일봉",
    "60m": "시간봉",
    "30m": "30분봉",
    "10m": "10분봉",
    "5m": "5분봉",
    "1m": "분봉",
}


def fetch_intraday_ohlcv(ticker: str, interval: str = "1m", count: int = 60):
    """장중 분봉·시간봉 수집 (pykrx 지원 범위 내)

    pykrx는 분봉/시간봉을 get_market_ohlcv_by_ticker()로 지원.
    """
    try:
        from pykrx import stock as pykrx_stock
        import pandas as pd

        today = date.today().strftime("%Y%m%d")

        # pykrx 분봉: freq='1'(1분), '5'(5분), '10', '30', '60'
        freq_map = {"1m": "1", "5m": "5", "10m": "10", "30m": "30", "60m": "60"}
        freq = freq_map.get(interval, "1")

        if interval == "1d":
            # 일봉은 기존 pykrx_client 사용
            from data.pykrx_client import fetch_ohlcv

            return fetch_ohlcv(ticker, start=date.today() - timedelta(days=count))

        df = pykrx_stock.get_market_ohlcv_by_ticker(today, market="ALL", freq=freq)

        # pykrx 분봉 응답 처리
        if ticker in df.index:
            row = df.loc[ticker]
            logger.info("분봉 수집 완료", ticker=ticker, interval=interval)
            return row
        else:
            logger.warning("분봉 데이터 없음", ticker=ticker, interval=interval)
            return None

    except Exception as e:
        logger.error("분봉 수집 실패", ticker=ticker, interval=interval, error=str(e))
        raise DataFetchError(f"분봉 수집 실패: {ticker}, {interval}") from e


class DataRefreshManager:
    """배치·수기 데이터 갱신 + 즉시 AI 분석 트리거 관리자

    사용법:
        manager = DataRefreshManager()
        manager.register_analysis_trigger(trigger_fn)  # AI 분석 콜백 등록
        manager.refresh_now("005930", data_types=["ohlcv", "news"])  # 수기 갱신
    """

    def __init__(self):
        self._analysis_triggers: list[Callable] = []
        self._refresh_lock = threading.Lock()
        self._last_refresh: dict[str, datetime] = {}

    def register_analysis_trigger(self, fn: Callable) -> None:
        """데이터 갱신 후 즉시 실행할 AI 분석 콜백 등록"""
        self._analysis_triggers.append(fn)
        logger.info("AI 분석 트리거 등록", trigger=fn.__name__)

    def refresh_now(
        self,
        tickers: Optional[list[str]] = None,
        data_types: Optional[list[str]] = None,
        trigger_analysis: bool = True,
    ) -> dict:
        """수기 즉시 갱신

        Args:
            tickers: 갱신할 종목 리스트 (None이면 전체 10개)
            data_types: ["ohlcv", "news", "intraday"] (None이면 전체)
            trigger_analysis: 갱신 후 AI 분석 즉시 실행 여부

        Returns:
            갱신 결과 딕셔너리
        """
        with self._refresh_lock:
            tickers = tickers or list(TOP_10_TICKERS.keys())
            data_types = data_types or ["ohlcv", "news"]

            results: dict = {"refreshed": [], "failed": [], "analysis_triggered": []}
            changed_tickers: list[str] = []

            for ticker in tickers:
                try:
                    refreshed = self._refresh_ticker(ticker, data_types)
                    if refreshed:
                        results["refreshed"].append(ticker)
                        changed_tickers.append(ticker)
                        self._last_refresh[ticker] = datetime.now()
                except Exception as e:
                    logger.error("갱신 실패", ticker=ticker, error=str(e))
                    results["failed"].append(ticker)

            # 변경된 종목에 대해 즉시 AI 분석 트리거
            if trigger_analysis and changed_tickers:
                for ticker in changed_tickers:
                    triggered = self._trigger_analysis(ticker)
                    if triggered:
                        results["analysis_triggered"].append(ticker)

            logger.info(
                "수기 갱신 완료",
                refreshed=len(results["refreshed"]),
                failed=len(results["failed"]),
                analysis_triggered=len(results["analysis_triggered"]),
            )
            return results

    def refresh_intraday_batch(self, interval: str = "5m", trigger_analysis: bool = True) -> dict:
        """분봉·시간봉 배치 갱신 (스케줄러에서 주기적 호출)

        Args:
            interval: "1m" | "5m" | "10m" | "30m" | "60m"
            trigger_analysis: 갱신 후 AI 분석 즉시 실행 여부
        """
        from scheduler.tasks import is_market_open

        if not is_market_open():
            logger.debug("장외 시간 - 분봉 갱신 스킵")
            return {"skipped": "market_closed"}

        results: dict = {"interval": interval, "refreshed": [], "failed": []}
        changed_tickers: list[str] = []

        for ticker in TOP_10_TICKERS:
            try:
                current = get_current_price(ticker)
                if current:
                    # 현재가를 인메모리 캐시 업데이트 (분봉 DB 저장은 별도)
                    _price_cache[ticker] = {"price": current, "updated_at": datetime.now()}
                    changed_tickers.append(ticker)
                    results["refreshed"].append(ticker)
            except Exception as e:
                logger.warning("분봉 갱신 실패", ticker=ticker, error=str(e))
                results["failed"].append(ticker)

        if trigger_analysis and changed_tickers:
            # 가격 변화가 큰 종목만 즉시 AI 분석 트리거
            significant_changes = self._detect_significant_changes(changed_tickers)
            for ticker in significant_changes:
                self._trigger_analysis(ticker)
                results.setdefault("analysis_triggered", []).append(ticker)

        return results

    def get_latest_prices(self) -> dict[str, dict]:
        """인메모리 최신 가격 캐시 반환"""
        return dict(_price_cache)

    def get_last_refresh_time(self, ticker: str) -> Optional[datetime]:
        return self._last_refresh.get(ticker)

    def _refresh_ticker(self, ticker: str, data_types: list[str]) -> bool:
        """단일 종목 데이터 갱신"""
        changed = False

        if "ohlcv" in data_types:
            from data.data_manager import upsert_ohlcv
            from data.pykrx_client import fetch_ohlcv

            df = fetch_ohlcv(ticker, start=date.today() - timedelta(days=5))
            if not df.empty:
                upsert_ohlcv(ticker, df)
                changed = True

        if "news" in data_types:
            from data.naver_scraper import fetch_news_headlines
            from core.models import NewsArticle

            articles = fetch_news_headlines(ticker, max_articles=5)
            with get_session() as session:
                for art in articles:
                    exists = (
                        session.query(NewsArticle)
                        .filter_by(ticker=ticker, title=art["title"])
                        .first()
                    )
                    if not exists:
                        session.add(
                            NewsArticle(
                                ticker=ticker,
                                title=art["title"],
                                source=art.get("source", "naver"),
                                published_at=art["published_at"],
                            )
                        )
                        changed = True

        return changed

    def _trigger_analysis(self, ticker: str) -> bool:
        """등록된 AI 분석 콜백 비동기 실행"""
        if not self._analysis_triggers:
            return False

        def _run():
            for fn in self._analysis_triggers:
                try:
                    fn(ticker)
                except Exception as e:
                    logger.error(
                        "AI 분석 트리거 실패", ticker=ticker, trigger=fn.__name__, error=str(e)
                    )

        thread = threading.Thread(target=_run, name=f"analysis-{ticker}", daemon=True)
        thread.start()
        logger.info("AI 분석 트리거 실행", ticker=ticker, async_=True)
        return True

    def _detect_significant_changes(
        self, tickers: list[str], threshold: float = 0.005
    ) -> list[str]:
        """가격 변화 0.5% 이상인 종목만 반환 (즉시 분석 필요)"""
        significant = []
        for ticker in tickers:
            cache = _price_cache.get(ticker)
            if not cache:
                continue
            prev_price = _prev_price_cache.get(ticker)
            if prev_price and abs(cache["price"] - prev_price) / prev_price >= threshold:
                significant.append(ticker)
            _prev_price_cache[ticker] = cache["price"]
        return significant


# 글로벌 인메모리 가격 캐시 (분봉 갱신용)
_price_cache: dict[str, dict] = {}
_prev_price_cache: dict[str, float] = {}

# 싱글턴 인스턴스
refresh_manager = DataRefreshManager()
