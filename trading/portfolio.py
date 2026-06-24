"""포트폴리오 상태 조회"""

from datetime import date

import structlog

from config.settings import settings
from core.database import get_session
from core.models import PortfolioSnapshot, Position, Trade
from data.pykrx_client import get_current_price

logger = structlog.get_logger(__name__)

_INITIAL_CASH = 10_000_000


def get_portfolio_state() -> dict:
    """현재 포트폴리오 상태 계산"""
    is_paper = not settings.is_live_trading

    with get_session() as session:
        positions_db = session.query(Position).filter_by(paper=is_paper).all()

        positions = []
        total_invested = 0.0

        for pos in positions_db:
            current_price = get_current_price(pos.ticker) or pos.avg_cost
            market_value = current_price * pos.quantity
            unrealized_pnl = (current_price - pos.avg_cost) * pos.quantity
            total_invested += market_value

            positions.append({
                "ticker": pos.ticker,
                "quantity": pos.quantity,
                "avg_cost": pos.avg_cost,
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl / (pos.avg_cost * pos.quantity) if pos.avg_cost > 0 else 0,
            })

        # 현금 계산
        trades = session.query(Trade).filter_by(paper=is_paper).all()
        cash_delta = sum(t.total_amount if t.side == "SELL" else -t.total_amount for t in trades)
        cash = _INITIAL_CASH + cash_delta

        total_value = cash + total_invested
        total_realized_pnl = sum(t.pnl or 0 for t in trades if t.side == "SELL")

        # 당일 손익 (오늘 체결된 거래)
        today_trades = [t for t in trades if t.executed_at and t.executed_at.date() == date.today()]
        daily_pnl = sum(t.pnl or 0 for t in today_trades if t.side == "SELL")

        return {
            "total_value": total_value,
            "cash": cash,
            "invested": total_invested,
            "daily_pnl": daily_pnl,
            "total_pnl": total_realized_pnl,
            "positions": positions,
            "paper": is_paper,
        }


def save_daily_snapshot() -> None:
    """당일 포트폴리오 스냅샷 저장"""
    state = get_portfolio_state()
    today = date.today()

    with get_session() as session:
        existing = session.query(PortfolioSnapshot).filter_by(snapshot_date=today).first()
        if existing:
            existing.total_value = state["total_value"]
            existing.cash = state["cash"]
            existing.invested = state["invested"]
            existing.daily_pnl = state["daily_pnl"]
            existing.total_pnl = state["total_pnl"]
        else:
            session.add(
                PortfolioSnapshot(
                    snapshot_date=today,
                    total_value=state["total_value"],
                    cash=state["cash"],
                    invested=state["invested"],
                    daily_pnl=state["daily_pnl"],
                    total_pnl=state["total_pnl"],
                    paper=state["paper"],
                )
            )

    logger.info("포트폴리오 스냅샷 저장", date=str(today), total_value=state["total_value"])
