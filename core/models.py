from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Stock(Base):
    __tablename__ = "stocks"

    ticker: str = Column(String(10), primary_key=True)
    name: str = Column(String(100), nullable=False)
    market: str = Column(String(20), nullable=False)  # KOSPI | KOSDAQ
    sector: Optional[str] = Column(String(100))
    is_active: bool = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, server_default=func.now())

    ohlcv_records = relationship("OHLCVDaily", back_populates="stock", lazy="select")
    news_articles = relationship("NewsArticle", back_populates="stock", lazy="select")


class OHLCVDaily(Base):
    __tablename__ = "ohlcv_daily"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    ticker: str = Column(String(10), ForeignKey("stocks.ticker"), nullable=False)
    date: date = Column(Date, nullable=False)
    open: float = Column(Float, nullable=False)
    high: float = Column(Float, nullable=False)
    low: float = Column(Float, nullable=False)
    close: float = Column(Float, nullable=False)
    volume: int = Column(Integer, nullable=False)
    created_at: datetime = Column(DateTime, server_default=func.now())

    stock = relationship("Stock", back_populates="ohlcv_records")

    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_ohlcv_ticker_date"),
        Index("ix_ohlcv_ticker_date", "ticker", "date"),
    )


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    ticker: str = Column(String(10), ForeignKey("stocks.ticker"), nullable=False)
    title: str = Column(String(500), nullable=False)
    body: Optional[str] = Column(Text)
    source: str = Column(String(50), default="naver")
    published_at: datetime = Column(DateTime, nullable=False)
    sentiment_score: Optional[float] = Column(Float)  # -1.0 ~ +1.0
    created_at: datetime = Column(DateTime, server_default=func.now())

    stock = relationship("Stock", back_populates="news_articles")

    __table_args__ = (Index("ix_news_ticker_published", "ticker", "published_at"),)


class AgentSession(Base):
    """AI 듀얼 에이전트 토론 세션"""

    __tablename__ = "agent_sessions"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    ticker: str = Column(String(10), ForeignKey("stocks.ticker"), nullable=False)
    session_date: date = Column(Date, nullable=False)
    total_rounds: int = Column(Integer, default=0)
    final_signal: Optional[str] = Column(String(10))  # BUY | SELL | HOLD
    final_confidence: Optional[float] = Column(Float)
    weighted_score: Optional[float] = Column(Float)
    exit_reason: Optional[str] = Column(String(50))  # CONSENSUS | MAX_ROUNDS | OSCILLATION | TIMEOUT | LOW_CONF
    execute_trade: bool = Column(Boolean, default=False)
    buy_price: Optional[float] = Column(Float)
    sell_price: Optional[float] = Column(Float)
    created_at: datetime = Column(DateTime, server_default=func.now())

    rounds = relationship("AgentRound", back_populates="session", order_by="AgentRound.round_number")

    __table_args__ = (Index("ix_session_ticker_date", "ticker", "session_date"),)


class AgentRound(Base):
    """AI 토론 각 라운드 기록"""

    __tablename__ = "agent_rounds"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    session_id: int = Column(Integer, ForeignKey("agent_sessions.id"), nullable=False)
    round_number: int = Column(Integer, nullable=False)
    agent: str = Column(String(20), nullable=False)  # claude | codex
    signal: str = Column(String(10), nullable=False)
    confidence: float = Column(Float, nullable=False)
    reasoning: str = Column(Text, nullable=False)
    key_factors: Optional[str] = Column(Text)  # JSON 배열
    risk_level: Optional[str] = Column(String(10))
    agreement: Optional[bool] = Column(Boolean)
    disagreement_points: Optional[str] = Column(Text)  # JSON 배열
    created_at: datetime = Column(DateTime, server_default=func.now())

    session = relationship("AgentSession", back_populates="rounds")


class Position(Base):
    """보유 포지션"""

    __tablename__ = "positions"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    ticker: str = Column(String(10), ForeignKey("stocks.ticker"), nullable=False)
    quantity: int = Column(Integer, nullable=False)
    avg_cost: float = Column(Float, nullable=False)
    current_price: Optional[float] = Column(Float)
    paper: bool = Column(Boolean, default=True)
    opened_at: datetime = Column(DateTime, server_default=func.now())
    updated_at: datetime = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("ticker", "paper", name="uq_position_ticker_paper"),
    )


class Trade(Base):
    """매매 이력"""

    __tablename__ = "trades"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    ticker: str = Column(String(10), ForeignKey("stocks.ticker"), nullable=False)
    side: str = Column(String(4), nullable=False)  # BUY | SELL
    quantity: int = Column(Integer, nullable=False)
    price: float = Column(Float, nullable=False)
    total_amount: float = Column(Float, nullable=False)
    pnl: Optional[float] = Column(Float)  # 실현손익 (매도 시)
    paper: bool = Column(Boolean, default=True)
    ai_signal: Optional[str] = Column(String(10))
    ai_confidence: Optional[float] = Column(Float)
    session_id: Optional[int] = Column(Integer, ForeignKey("agent_sessions.id"))
    executed_at: datetime = Column(DateTime, server_default=func.now())

    __table_args__ = (Index("ix_trades_ticker_executed", "ticker", "executed_at"),)


class PortfolioSnapshot(Base):
    """일별 포트폴리오 스냅샷"""

    __tablename__ = "portfolio_snapshots"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: date = Column(Date, nullable=False, unique=True)
    total_value: float = Column(Float, nullable=False)
    cash: float = Column(Float, nullable=False)
    invested: float = Column(Float, nullable=False)
    daily_pnl: float = Column(Float, default=0.0)
    total_pnl: float = Column(Float, default=0.0)
    paper: bool = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, server_default=func.now())
