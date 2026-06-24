"""AI 듀얼 에이전트 공유 데이터 구조"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class ExitReason(str, Enum):
    CONSENSUS = "CONSENSUS"  # 합의 달성 (정상 종료)
    MAX_ROUNDS = "MAX_ROUNDS"  # 최대 라운드 도달
    OSCILLATION = "OSCILLATION"  # 신호 교대 반복 (교착)
    TIMEOUT = "TIMEOUT"  # CLI 타임아웃
    LOW_CONFIDENCE = "LOW_CONFIDENCE"  # 신뢰도 하한 미달
    CLI_ERROR = "CLI_ERROR"  # CLI 실행 오류


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class PriorSessionSummary:
    """과거 토론 세션 요약 (세션 간 연속성에 사용 - 동일 종목의 직전 N개 분석)"""

    session_date: str
    final_signal: Signal
    final_confidence: float
    exit_reason: ExitReason
    last_reasoning: str


@dataclass
class MarketContext:
    """AI 에이전트에 전달되는 시장 데이터"""

    ticker: str
    company_name: str
    current_price: float
    day_change_pct: float
    ohlcv_20d: list[dict]  # 최근 20일 [{date,open,high,low,close,volume}]
    indicators: dict  # 기술 지표 dict
    news_headlines: list[str]  # 최근 5-10개 뉴스 제목
    volume_ratio: float  # 당일 거래량 / 20일 평균
    market_date: str  # 분석 기준일 (YYYY-MM-DD)
    news_sentiment: Optional[float] = None  # 최근 뉴스 감성 점수 평균 (-1.0~+1.0)
    prior_sessions: list[PriorSessionSummary] = field(default_factory=list)  # 동일 종목 과거 분석


@dataclass
class AgentMessage:
    """각 라운드의 AI 응답"""

    round_number: int
    agent: str  # "claude" | "codex"
    signal: Signal
    confidence: float  # 0.0~1.0
    reasoning: str
    key_factors: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    agreement: Optional[bool] = None  # Round 2+: 이전 AI 동의 여부
    disagreement_points: list[str] = field(default_factory=list)
    signal_changed: Optional[bool] = None  # Round 3+
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def signal_score(self) -> float:
        """BUY=+1, HOLD=0, SELL=-1"""
        return {"BUY": 1.0, "HOLD": 0.0, "SELL": -1.0}[self.signal.value]

    @property
    def weighted_contribution(self) -> float:
        return self.signal_score * self.confidence


@dataclass
class ConsensusResult:
    """최종 합의 결과"""

    final_signal: Signal
    final_confidence: float
    weighted_score: float  # -1.0 ~ +1.0
    total_rounds: int
    exit_reason: ExitReason
    agreement: bool  # 두 AI 최종 신호 일치 여부
    execute_trade: bool
    buy_price: Optional[float] = None
    sell_price: Optional[float] = None
    fallback_used: bool = False
    rationale: str = ""
    messages: list[AgentMessage] = field(default_factory=list)
