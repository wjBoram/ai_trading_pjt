"""APScheduler 작업 정의"""

from datetime import date, datetime
from typing import Optional

import pytz
import structlog

from config.market_calendar import is_market_holiday

logger = structlog.get_logger(__name__)

KST = pytz.timezone("Asia/Seoul")


def is_trading_day(target: Optional[date] = None) -> bool:
    """해당 날짜가 거래일인지 확인 (평일 + KRX 휴장일 아님). 시간대는 고려하지 않음.

    CronTrigger는 `day_of_week=mon-fri`로 주말을 걸러내지만 한국 공휴일은 알지
    못하므로, 일 1회짜리 작업(premarket/morning_analysis/news_refresh/eod_snapshot)은
    이 함수로 휴장일을 직접 확인해야 한다.
    """
    target = target or datetime.now(KST).date()
    if target.weekday() >= 5:  # 토·일
        return False
    return not is_market_holiday(target)


def is_market_open() -> bool:
    """장중 여부 확인 (09:00~15:30 KST, 거래일 한정)"""
    now = datetime.now(KST)
    if not is_trading_day(now.date()):
        return False
    market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


def job_premarket_data() -> None:
    """08:50 KST: 전일 OHLCV + 지표 갱신"""
    if not is_trading_day():
        logger.info("휴장일 - 장전 데이터 수집 스킵")
        return

    from data.data_manager import refresh_daily_ohlcv

    logger.info("장전 데이터 수집 시작")
    refresh_daily_ohlcv()
    logger.info("장전 데이터 수집 완료")


def job_morning_analysis() -> None:
    """09:10 KST: AI 토론 실행 + 매매 신호"""
    if not is_trading_day():
        logger.info("휴장일 - AI 분석 스킵")
        return
    _run_analysis_for_all_tickers()


def job_intraday_refresh() -> None:
    """장중 5분마다: 현재가 갱신 + 의미 있는 변화 시 즉시 AI 재분석"""
    if not is_market_open():
        return

    from data.realtime_collector import refresh_manager

    result = refresh_manager.refresh_intraday_batch(interval="5m", trigger_analysis=True)
    if result.get("analysis_triggered"):
        logger.info("장중 즉시 AI 재분석 트리거", tickers=result["analysis_triggered"])


def job_news_refresh() -> None:
    """16:00 KST: 뉴스 수집 + AI 분석 트리거"""
    if not is_trading_day():
        logger.info("휴장일 - 뉴스 갱신 스킵")
        return

    from data.data_manager import refresh_news

    logger.info("뉴스 수집 시작")
    refresh_news()

    # 뉴스 갱신 후 AI 재분석
    _run_analysis_for_all_tickers(reason="news_update")


def job_eod_snapshot() -> None:
    """15:40 KST: 포트폴리오 스냅샷 저장"""
    if not is_trading_day():
        logger.info("휴장일 - 스냅샷 스킵")
        return

    from trading.portfolio import save_daily_snapshot

    save_daily_snapshot()
    logger.info("포트폴리오 스냅샷 저장 완료")


def run_analysis_for_ticker(ticker: str, reason: str = "scheduled") -> None:
    """단일 종목 AI 분석 실행 (realtime_collector 트리거 콜백으로 등록)"""
    from agents.orchestrator import get_recent_sessions, run_debate, save_session_to_db
    from agents.protocol import MarketContext
    from data.data_manager import get_recent_news, get_recent_ohlcv
    from data.pykrx_client import TOP_10_TICKERS, get_current_price
    from data.sentiment import aggregate_sentiment
    from indicators.technical import get_latest_indicators
    from trading.order_executor import execute_signal

    name = TOP_10_TICKERS.get(ticker, ticker)
    try:
        df = get_recent_ohlcv(ticker, days=60)
        if df.empty:
            logger.warning("OHLCV 없음 - AI 분석 스킵", ticker=ticker)
            return

        indicators = get_latest_indicators(df) or {}
        news = get_recent_news(ticker, max_articles=8)
        headlines = [n["title"] for n in news]
        news_sentiment = aggregate_sentiment([n["sentiment_score"] for n in news])
        prior_sessions = get_recent_sessions(ticker)
        current_price = get_current_price(ticker) or indicators.get("close", 0)

        if not current_price:
            return

        ctx = MarketContext(
            ticker=ticker,
            company_name=name,
            current_price=current_price,
            day_change_pct=float(indicators.get("return_1d") or 0) * 100,
            ohlcv_20d=df.tail(20).to_dict("records"),
            indicators=indicators,
            news_headlines=headlines,
            volume_ratio=float(indicators.get("volume_ratio") or 1.0),
            market_date=str(df["date"].iloc[-1]),
            news_sentiment=news_sentiment,
            prior_sessions=prior_sessions,
        )

        logger.info("AI 분석 시작", ticker=ticker, reason=reason)
        result = run_debate(ctx)
        session_id = save_session_to_db(ticker, result)

        if result.execute_trade:
            execute_signal(ticker, result, session_id)

    except Exception as e:
        logger.error("종목 AI 분석 실패", ticker=ticker, reason=reason, error=str(e))


def _run_analysis_for_all_tickers(reason: str = "scheduled") -> None:
    """전체 상위 10개 종목 AI 분석"""
    from data.pykrx_client import TOP_10_TICKERS

    logger.info("전체 AI 분석 시작", tickers=list(TOP_10_TICKERS.keys()), reason=reason)
    for ticker in TOP_10_TICKERS:
        run_analysis_for_ticker(ticker, reason=reason)
    logger.info("전체 AI 분석 완료")
