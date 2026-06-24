"""FastAPI 진입점"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.logging_config import setup_logging
from config.settings import settings
from core.database import init_db
from scheduler.job_runner import create_scheduler
from api.routes.refresh import router as refresh_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level, settings.log_file)
    init_db()

    scheduler = create_scheduler()
    scheduler.start()

    yield

    scheduler.shutdown()


app = FastAPI(
    title="국내주식 AI 자동매매 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(refresh_router)


@app.get("/health")
async def health():
    return {"status": "ok", "trading_mode": settings.trading_mode}


@app.get("/api/portfolio")
async def get_portfolio():
    from trading.portfolio import get_portfolio_state
    return get_portfolio_state()


@app.get("/api/stocks")
async def get_stocks():
    from data.pykrx_client import TOP_10_TICKERS
    return {"tickers": TOP_10_TICKERS}


@app.get("/api/stocks/{ticker}/ohlcv")
async def get_ohlcv(ticker: str, days: int = 60):
    from data.data_manager import get_recent_ohlcv
    df = get_recent_ohlcv(ticker, days=days)
    if df.empty:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="데이터 없음")
    return df.to_dict("records")


@app.get("/api/sessions")
async def get_sessions(limit: int = 20):
    from core.database import get_session
    from core.models import AgentSession
    with get_session() as session:
        sessions = (
            session.query(AgentSession)
            .order_by(AgentSession.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": s.id,
                "ticker": s.ticker,
                "session_date": str(s.session_date),
                "final_signal": s.final_signal,
                "final_confidence": s.final_confidence,
                "exit_reason": s.exit_reason,
                "execute_trade": s.execute_trade,
            }
            for s in sessions
        ]


@app.get("/api/trades")
async def get_trades(limit: int = 50, ticker: str | None = None):
    from core.database import get_session
    from core.models import Trade
    with get_session() as session:
        query = session.query(Trade).order_by(Trade.executed_at.desc())
        if ticker:
            query = query.filter_by(ticker=ticker)
        trades = query.limit(limit).all()
        return [
            {
                "id": t.id,
                "ticker": t.ticker,
                "side": t.side,
                "quantity": t.quantity,
                "price": t.price,
                "total_amount": t.total_amount,
                "pnl": t.pnl,
                "paper": t.paper,
                "ai_signal": t.ai_signal,
                "executed_at": str(t.executed_at),
            }
            for t in trades
        ]


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
