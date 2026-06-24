"""APScheduler 장중 작업 오케스트레이션"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import pytz
import structlog

from scheduler.tasks import (
    job_eod_snapshot,
    job_intraday_refresh,
    job_morning_analysis,
    job_news_refresh,
    job_premarket_data,
    run_analysis_for_ticker,
)

logger = structlog.get_logger(__name__)
KST = pytz.timezone("Asia/Seoul")


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=KST)

    # 08:50 KST: 장전 OHLCV 갱신
    scheduler.add_job(
        job_premarket_data,
        CronTrigger(hour=8, minute=50, timezone=KST, day_of_week="mon-fri"),
        id="premarket_data",
        max_instances=1,
        coalesce=True,
    )

    # 09:10 KST: AI 토론 + 매매 신호
    scheduler.add_job(
        job_morning_analysis,
        CronTrigger(hour=9, minute=10, timezone=KST, day_of_week="mon-fri"),
        id="morning_analysis",
        max_instances=1,
        coalesce=True,
    )

    # 장중 5분마다: 현재가 갱신 + 즉시 AI 재분석 트리거
    scheduler.add_job(
        job_intraday_refresh,
        IntervalTrigger(minutes=5),
        id="intraday_refresh",
        max_instances=1,
        coalesce=True,
    )

    # 15:40 KST: 장 마감 스냅샷
    scheduler.add_job(
        job_eod_snapshot,
        CronTrigger(hour=15, minute=40, timezone=KST, day_of_week="mon-fri"),
        id="eod_snapshot",
        max_instances=1,
        coalesce=True,
    )

    # 16:00 KST: 뉴스 수집 + AI 재분석
    scheduler.add_job(
        job_news_refresh,
        CronTrigger(hour=16, minute=0, timezone=KST, day_of_week="mon-fri"),
        id="news_refresh",
        max_instances=1,
        coalesce=True,
    )

    # DataRefreshManager에 AI 분석 트리거 콜백 등록
    from data.realtime_collector import refresh_manager
    refresh_manager.register_analysis_trigger(run_analysis_for_ticker)

    logger.info("스케줄러 작업 등록 완료")
    return scheduler
