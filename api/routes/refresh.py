"""데이터 수기 갱신 REST API"""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from data.realtime_collector import refresh_manager

router = APIRouter(prefix="/api/refresh", tags=["data-refresh"])


class RefreshRequest(BaseModel):
    tickers: Optional[list[str]] = None          # None이면 전체 10개 종목
    data_types: Optional[list[str]] = None       # ["ohlcv", "news"]
    trigger_analysis: bool = True                # 갱신 후 AI 분석 즉시 실행


class IntradayRefreshRequest(BaseModel):
    interval: str = "5m"                         # "1m"|"5m"|"10m"|"30m"|"60m"
    trigger_analysis: bool = True


@router.post("/manual")
async def manual_refresh(req: RefreshRequest, background_tasks: BackgroundTasks):
    """수기 즉시 갱신 (비동기 실행)

    Example:
        POST /api/refresh/manual
        {"tickers": ["005930"], "data_types": ["ohlcv", "news"], "trigger_analysis": true}
    """
    # 비동기 실행 (응답 즉시 반환, 갱신은 백그라운드)
    background_tasks.add_task(
        refresh_manager.refresh_now,
        tickers=req.tickers,
        data_types=req.data_types,
        trigger_analysis=req.trigger_analysis,
    )
    return {
        "status": "accepted",
        "message": "갱신 작업이 백그라운드에서 실행됩니다",
        "tickers": req.tickers or "all",
        "data_types": req.data_types or ["ohlcv", "news"],
        "trigger_analysis": req.trigger_analysis,
    }


@router.post("/manual/sync")
async def manual_refresh_sync(req: RefreshRequest):
    """수기 즉시 갱신 (동기, 완료까지 대기)"""
    result = refresh_manager.refresh_now(
        tickers=req.tickers,
        data_types=req.data_types,
        trigger_analysis=req.trigger_analysis,
    )
    return {"status": "completed", "result": result}


@router.post("/intraday")
async def intraday_refresh(req: IntradayRefreshRequest, background_tasks: BackgroundTasks):
    """분봉·시간봉 수기 갱신"""
    valid_intervals = ["1m", "5m", "10m", "30m", "60m", "1d"]
    if req.interval not in valid_intervals:
        raise HTTPException(status_code=400, detail=f"interval은 {valid_intervals} 중 하나여야 합니다")

    background_tasks.add_task(
        refresh_manager.refresh_intraday_batch,
        interval=req.interval,
        trigger_analysis=req.trigger_analysis,
    )
    return {"status": "accepted", "interval": req.interval}


@router.get("/prices")
async def get_latest_prices():
    """인메모리 최신 가격 캐시 조회"""
    prices = refresh_manager.get_latest_prices()
    return {
        ticker: {
            "price": info["price"],
            "updated_at": info["updated_at"].isoformat(),
        }
        for ticker, info in prices.items()
    }


@router.get("/status")
async def get_refresh_status():
    """각 종목의 마지막 갱신 시각 조회"""
    from data.pykrx_client import TOP_10_TICKERS

    return {
        ticker: {
            "name": name,
            "last_refresh": (
                refresh_manager.get_last_refresh_time(ticker).isoformat()
                if refresh_manager.get_last_refresh_time(ticker)
                else None
            ),
        }
        for ticker, name in TOP_10_TICKERS.items()
    }
