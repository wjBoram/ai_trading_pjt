"""모의거래 시뮬레이터 (기본값)"""

from datetime import datetime
from typing import Optional

import structlog

from core.database import get_session
from core.exceptions import TradingError
from core.models import Position, Trade

logger = structlog.get_logger(__name__)

_INITIAL_CASH = 10_000_000  # 초기 자금 1,000만원 (설정 가능)


class PaperBroker:
    """Paper Trading - DB 기반 모의 매매"""

    def get_cash(self) -> float:
        """가용 현금 조회 (전체 - 투자금)"""
        with get_session() as session:
            invested = sum(
                p.avg_cost * p.quantity
                for p in session.query(Position).filter_by(paper=True).all()
            )
            total_trades_cash = self._calc_cash_from_trades(session)
            return _INITIAL_CASH + total_trades_cash - invested

    def get_positions(self) -> list[dict]:
        with get_session() as session:
            return [
                {
                    "ticker": p.ticker,
                    "quantity": p.quantity,
                    "avg_cost": p.avg_cost,
                    "opened_at": p.opened_at,
                }
                for p in session.query(Position).filter_by(paper=True).all()
            ]

    def buy(
        self,
        ticker: str,
        quantity: int,
        price: float,
        ai_signal: Optional[str] = None,
        ai_confidence: Optional[float] = None,
        session_id: Optional[int] = None,
    ) -> Trade:
        """모의 매수"""
        total_amount = quantity * price
        cash = self.get_cash()

        if total_amount > cash:
            raise TradingError(f"현금 부족: {total_amount:,.0f}원 > {cash:,.0f}원")

        with get_session() as session:
            # 포지션 업데이트
            pos = session.query(Position).filter_by(ticker=ticker, paper=True).first()
            if pos:
                new_qty = pos.quantity + quantity
                pos.avg_cost = (pos.avg_cost * pos.quantity + price * quantity) / new_qty
                pos.quantity = new_qty
            else:
                session.add(Position(ticker=ticker, quantity=quantity, avg_cost=price, paper=True))

            # 거래 기록
            trade = Trade(
                ticker=ticker,
                side="BUY",
                quantity=quantity,
                price=price,
                total_amount=total_amount,
                paper=True,
                ai_signal=ai_signal,
                ai_confidence=ai_confidence,
                session_id=session_id,
            )
            session.add(trade)
            session.flush()
            trade_id = trade.id

        logger.info("모의 매수", ticker=ticker, quantity=quantity, price=price, total=total_amount)
        return trade

    def sell(
        self,
        ticker: str,
        quantity: int,
        price: float,
        ai_signal: Optional[str] = None,
        ai_confidence: Optional[float] = None,
        session_id: Optional[int] = None,
    ) -> Trade:
        """모의 매도"""
        with get_session() as session:
            pos = session.query(Position).filter_by(ticker=ticker, paper=True).first()
            if not pos or pos.quantity < quantity:
                raise TradingError(f"보유 수량 부족: {ticker}")

            total_amount = quantity * price
            pnl = (price - pos.avg_cost) * quantity

            # 포지션 업데이트
            pos.quantity -= quantity
            if pos.quantity == 0:
                session.delete(pos)

            # 거래 기록
            trade = Trade(
                ticker=ticker,
                side="SELL",
                quantity=quantity,
                price=price,
                total_amount=total_amount,
                pnl=pnl,
                paper=True,
                ai_signal=ai_signal,
                ai_confidence=ai_confidence,
                session_id=session_id,
            )
            session.add(trade)

        logger.info("모의 매도", ticker=ticker, quantity=quantity, price=price, pnl=pnl)
        return trade

    def _calc_cash_from_trades(self, session) -> float:
        """거래 이력에서 현금 증감 계산"""
        trades = session.query(Trade).filter_by(paper=True).all()
        cash_delta = 0.0
        for t in trades:
            if t.side == "SELL":
                cash_delta += t.total_amount
            else:
                cash_delta -= t.total_amount
        return cash_delta


paper_broker = PaperBroker()
