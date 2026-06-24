from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # KIS OpenAPI
    kis_app_key: str = Field(default="", description="KIS OpenAPI App Key")
    kis_app_secret: str = Field(default="", description="KIS OpenAPI App Secret")
    kis_account_number: str = Field(default="", description="KIS 계좌번호")
    kis_account_product_code: str = Field(default="01")
    kis_base_url: str = Field(default="https://openapivts.koreainvestment.com:9443")

    # AI API Keys
    anthropic_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")

    # Trading Mode
    trading_mode: str = Field(default="paper")  # paper | live

    # AI Agent Settings
    max_rounds: int = Field(default=5)
    convergence_conf: float = Field(default=0.65)
    min_confidence: float = Field(default=0.40)
    timeout_per_round: int = Field(default=120)
    oscillation_window: int = Field(default=3)
    prior_sessions_limit: int = Field(default=3)  # 세션 간 연속성: 동일 종목 과거 세션 조회 개수

    # Risk Management
    max_position_pct: float = Field(default=0.20)
    stop_loss_pct: float = Field(default=0.05)
    daily_loss_limit_pct: float = Field(default=0.03)
    max_open_positions: int = Field(default=5)
    min_trade_confidence: float = Field(default=0.65)

    # Database
    db_path: str = Field(default="data_store/trading.db")

    # Logging
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="data_store/logs/trading.log")

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    @property
    def is_live_trading(self) -> bool:
        return self.trading_mode.lower() == "live"


settings = Settings()
