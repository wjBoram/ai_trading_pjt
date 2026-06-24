class StockAIError(Exception):
    """프로젝트 기본 예외"""


class DataFetchError(StockAIError):
    """외부 데이터 수집 실패"""


class KISAPIError(StockAIError):
    """KIS OpenAPI 오류"""


class KISAuthError(KISAPIError):
    """KIS 인증 실패"""


class TradingError(StockAIError):
    """매매 처리 오류"""


class RiskLimitError(TradingError):
    """리스크 한도 초과"""


class AgentError(StockAIError):
    """AI 에이전트 실행 오류"""


class AgentTimeoutError(AgentError):
    """CLI 타임아웃"""


class AgentParseError(AgentError):
    """AI 응답 파싱 실패"""


class ConfigError(StockAIError):
    """설정 오류"""
