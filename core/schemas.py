from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class StockSchema(BaseModel):
    ticker: str
    name: str
    market: str
    sector: Optional[str] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class OHLCVSchema(BaseModel):
    ticker: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int

    model_config = {"from_attributes": True}


class AgentRoundSchema(BaseModel):
    round_number: int
    agent: str
    signal: str
    confidence: float
    reasoning: str
    key_factors: Optional[list[str]] = None
    risk_level: Optional[str] = None
    agreement: Optional[bool] = None
    disagreement_points: Optional[list[str]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentSessionSchema(BaseModel):
    id: int
    ticker: str
    session_date: date
    total_rounds: int
    final_signal: Optional[str] = None
    final_confidence: Optional[float] = None
    weighted_score: Optional[float] = None
    exit_reason: Optional[str] = None
    execute_trade: bool
    buy_price: Optional[float] = None
    sell_price: Optional[float] = None
    rounds: list[AgentRoundSchema] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class TradeSchema(BaseModel):
    id: int
    ticker: str
    side: str
    quantity: int
    price: float
    total_amount: float
    pnl: Optional[float] = None
    paper: bool
    ai_signal: Optional[str] = None
    ai_confidence: Optional[float] = None
    executed_at: datetime

    model_config = {"from_attributes": True}


class PositionSchema(BaseModel):
    id: int
    ticker: str
    quantity: int
    avg_cost: float
    current_price: Optional[float] = None
    paper: bool
    unrealized_pnl: Optional[float] = Field(default=None)

    model_config = {"from_attributes": True}

    @property
    def unrealized_pnl_calc(self) -> Optional[float]:
        if self.current_price is None:
            return None
        return (self.current_price - self.avg_cost) * self.quantity


class PortfolioSummarySchema(BaseModel):
    total_value: float
    cash: float
    invested: float
    daily_pnl: float
    total_pnl: float
    positions: list[PositionSchema]
    paper: bool
