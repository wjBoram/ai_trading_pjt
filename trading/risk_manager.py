"""리스크 관리 - 절대 우회 불가"""

from typing import Optional

import structlog

from config.settings import settings
from core.exceptions import RiskLimitError

logger = structlog.get_logger(__name__)


class RiskManager:
    """모든 주문은 이 클래스의 승인을 거쳐야 함"""

    def approve_buy(
        self,
        ticker: str,
        quantity: int,
        price: float,
        portfolio_value: float,
        available_cash: float,
        open_positions_count: int,
        ai_confidence: float,
        daily_pnl: float,
    ) -> tuple[bool, str]:
        """매수 승인 여부 반환 (approved, reason)"""

        order_amount = quantity * price

        # 1. AI 신뢰도 최소 기준
        if ai_confidence < settings.min_trade_confidence:
            return False, f"AI 신뢰도 미달: {ai_confidence:.0%} < {settings.min_trade_confidence:.0%}"

        # 2. 최대 보유 종목 수
        if open_positions_count >= settings.max_open_positions:
            return False, f"최대 보유 종목 초과: {open_positions_count}/{settings.max_open_positions}"

        # 3. 일일 손실 한도 (새 매수만 차단, 손절 매도는 허용)
        if portfolio_value > 0:
            daily_loss_pct = daily_pnl / portfolio_value
            if daily_loss_pct < -settings.daily_loss_limit_pct:
                return False, f"일일 손실 한도 초과: {daily_loss_pct:.2%}"

        # 4. 종목당 최대 비중
        if portfolio_value > 0:
            position_pct = order_amount / portfolio_value
            if position_pct > settings.max_position_pct:
                return False, f"종목당 최대 비중 초과: {position_pct:.2%} > {settings.max_position_pct:.0%}"

        # 5. 현금 충분 여부
        if order_amount > available_cash:
            return False, f"현금 부족: 필요 {order_amount:,.0f}원 > 가용 {available_cash:,.0f}원"

        logger.info("매수 승인", ticker=ticker, quantity=quantity, price=price, amount=order_amount)
        return True, "승인"

    def check_stop_loss(
        self,
        ticker: str,
        avg_cost: float,
        current_price: float,
    ) -> tuple[bool, str]:
        """손절 조건 확인 (True = 즉시 매도 필요)"""
        if avg_cost <= 0:
            return False, ""

        loss_pct = (current_price - avg_cost) / avg_cost
        if loss_pct < -settings.stop_loss_pct:
            reason = f"손절 발동: {loss_pct:.2%} (한도: -{settings.stop_loss_pct:.0%})"
            logger.warning("손절 발동", ticker=ticker, loss_pct=f"{loss_pct:.2%}", avg_cost=avg_cost)
            return True, reason

        return False, ""

    def calc_position_size(
        self,
        portfolio_value: float,
        available_cash: float,
        price: float,
        confidence: float,
    ) -> int:
        """포지션 크기 계산 (주 단위)

        신뢰도 비례 + 최대 비중 제한
        """
        target_pct = min(confidence * settings.max_position_pct, settings.max_position_pct)
        target_amount = min(portfolio_value * target_pct, available_cash * 0.95)

        if price <= 0:
            return 0

        quantity = int(target_amount / price)
        return max(1, quantity) if target_amount >= price else 0


risk_manager = RiskManager()
