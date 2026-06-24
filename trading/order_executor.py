"""실거래 vs 모의거래 라우팅"""

from typing import Optional

import structlog

from agents.protocol import ConsensusResult, Signal
from config.settings import settings
from core.exceptions import TradingError
from core.models import Trade
from data.pykrx_client import get_current_price
from trading.paper_broker import paper_broker
from trading.portfolio import get_portfolio_state
from trading.risk_manager import risk_manager

logger = structlog.get_logger(__name__)


def execute_signal(ticker: str, result: ConsensusResult, session_id: Optional[int] = None) -> Optional[Trade]:
    """AI 합의 결과에 따라 주문 실행"""

    if not result.execute_trade:
        logger.info("거래 미실행 - execute_trade=False", ticker=ticker, exit_reason=result.exit_reason.value)
        return None

    current_price = get_current_price(ticker) or result.buy_price
    if not current_price:
        logger.warning("현재가 조회 실패 - 거래 취소", ticker=ticker)
        return None

    portfolio = get_portfolio_state()
    open_positions = len(portfolio["positions"])

    if result.final_signal == Signal.BUY:
        return _execute_buy(ticker, current_price, result, portfolio, open_positions, session_id)
    elif result.final_signal == Signal.SELL:
        return _execute_sell(ticker, current_price, result, session_id)

    return None


def _execute_buy(
    ticker: str,
    price: float,
    result: ConsensusResult,
    portfolio: dict,
    open_positions: int,
    session_id: Optional[int],
) -> Optional[Trade]:
    quantity = risk_manager.calc_position_size(
        portfolio_value=portfolio["total_value"],
        available_cash=portfolio["cash"],
        price=price,
        confidence=result.final_confidence,
    )

    if quantity <= 0:
        logger.warning("매수 수량 0 - 거래 취소", ticker=ticker)
        return None

    approved, reason = risk_manager.approve_buy(
        ticker=ticker,
        quantity=quantity,
        price=price,
        portfolio_value=portfolio["total_value"],
        available_cash=portfolio["cash"],
        open_positions_count=open_positions,
        ai_confidence=result.final_confidence,
        daily_pnl=portfolio.get("daily_pnl", 0),
    )

    if not approved:
        logger.warning("매수 리스크 거부", ticker=ticker, reason=reason)
        return None

    if settings.is_live_trading:
        return _kis_buy(ticker, quantity, price, result, session_id)
    else:
        return paper_broker.buy(
            ticker=ticker,
            quantity=quantity,
            price=price,
            ai_signal=result.final_signal.value,
            ai_confidence=result.final_confidence,
            session_id=session_id,
        )


def _execute_sell(
    ticker: str,
    price: float,
    result: ConsensusResult,
    session_id: Optional[int],
) -> Optional[Trade]:
    """보유 포지션 전량 매도"""
    positions = paper_broker.get_positions() if not settings.is_live_trading else []
    pos = next((p for p in positions if p["ticker"] == ticker), None)

    if not pos:
        logger.info("보유 포지션 없음 - 매도 스킵", ticker=ticker)
        return None

    if settings.is_live_trading:
        return _kis_sell(ticker, pos["quantity"], price, result, session_id)
    else:
        return paper_broker.sell(
            ticker=ticker,
            quantity=pos["quantity"],
            price=price,
            ai_signal=result.final_signal.value,
            ai_confidence=result.final_confidence,
            session_id=session_id,
        )


def check_and_execute_stop_loss(ticker: str, current_price: float) -> Optional[Trade]:
    """손절 조건 확인 및 자동 매도"""
    positions = paper_broker.get_positions() if not settings.is_live_trading else []
    pos = next((p for p in positions if p["ticker"] == ticker), None)

    if not pos:
        return None

    triggered, reason = risk_manager.check_stop_loss(
        ticker=ticker,
        avg_cost=pos["avg_cost"],
        current_price=current_price,
    )

    if triggered:
        logger.warning("손절 자동 매도 실행", ticker=ticker, reason=reason)
        if settings.is_live_trading:
            return _kis_sell(ticker, pos["quantity"], current_price, None, None)
        else:
            return paper_broker.sell(
                ticker=ticker,
                quantity=pos["quantity"],
                price=current_price,
                ai_signal="STOP_LOSS",
            )

    return None


def _kis_buy(ticker, quantity, price, result, session_id) -> Optional[Trade]:
    """KIS 실거래 매수 (Phase 3에서 구현)"""
    logger.info("KIS 실거래 매수 (미구현)", ticker=ticker, quantity=quantity, price=price)
    raise NotImplementedError("KIS 실거래 매수는 Phase 3 (data/kis_client.py) 구현 후 활성화")


def _kis_sell(ticker, quantity, price, result, session_id) -> Optional[Trade]:
    """KIS 실거래 매도 (Phase 3에서 구현)"""
    logger.info("KIS 실거래 매도 (미구현)", ticker=ticker, quantity=quantity, price=price)
    raise NotImplementedError("KIS 실거래 매도는 Phase 3 (data/kis_client.py) 구현 후 활성화")
