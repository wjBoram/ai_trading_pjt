# 변경 이력 (CHANGELOG)

변경 이력 형식: [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/) 기반

---

## [Unreleased]

### Added (데이터 수집 가이드라인 + 월/주/연봉 아카이브 + 휴장일 캘린더, v1.3→v1.4)
- `docs/DATA_COLLECTION_ARCHITECTURE.md`: 데이터 수집/아키텍처 가이드라인 신규 작성
- `data/pykrx_client.py`: `fetch_ohlcv_monthly()`/`fetch_ohlcv_yearly()`(pykrx freq='m'/'y'),
  `fetch_ohlcv_weekly()`(일봉 resample 파생), 공통 헬퍼 `_normalize_ohlcv_df()`/`_fetch_ohlcv_with_freq()`로 리팩터링
- `scripts/collect_price_archive.py`: 종목+시간단위 단위로 1년치(기본) 가격을 JSON 아카이브로
  수집(`--ticker`, `--timeframe`, `--days`). 일봉은 기존 DB도 함께 갱신, `ARCHIVE_INDEX.md` 자동 갱신
- `scripts/load_price_archive.py`: JSON 아카이브를 읽어 `OHLCVDaily` 재적재(현재 일봉만)
- `config/market_calendar.py`: KRX 휴장일 정적 연간 캘린더(`is_market_holiday()`), 2026년분 등록
- `scheduler/tasks.py`: `is_trading_day()` 추가, `is_market_open()`과 일 1회 스케줄 작업 4개
  (premarket/morning_analysis/news_refresh/eod_snapshot)에 휴장일 가드 적용
- `tests/unit/test_price_archive.py`, `tests/unit/test_market_calendar.py`: 신규 단위 테스트 12개
- `docs/REQUIREMENTS.md`: D-13/D-14/D-15 추가, D-06 상태를 "✅완료"→"⚠️오류"로 정정
  (pykrx 분봉 미지원 + 기존 구현 버그를 직접 코드 확인으로 검증), v1.3→v1.4 변경 이력 기록

### Changed
- `data/data_manager.py`: `_upsert_ohlcv()` → `upsert_ohlcv()` (이미 `realtime_collector.py`에서
  cross-module로 쓰이고 있었고, 신규 아카이브 스크립트도 재사용해야 해서 공개 함수로 승격)

### Added (Codex 규칙 및 Claude–Codex 협업)
- 루트 `AGENTS.md`: Codex 표준 프로젝트 규칙, paper/live 안전 경계, 데이터·예측·거래 불변조건 추가
- `docs/CLAUDE_CODEX_WORKFLOW.md`: 단일 작성자, handoff, read-only 교차 리뷰 표준 추가
- `docs/PROJECT_REVIEW_2026-06-24.md`: 현재 구현의 P0~P2 finding과 단계별 최적화 로드맵 추가
- `CLAUDE.md`, `README.md`: 새 Codex/협업/리뷰 문서 진입점 연결

### Added
- **분석 방법론 조사 + 1단계(즉시 적용) 구현**
  - `docs/ANALYSIS_METHODS.md`: 외부 분석/예측 방법론 조사 문서 신규 작성
  - `data/sentiment.py`: 뉴스 감성분석 점수화 (사전/키워드 기반, `score_text_sentiment`,
    `aggregate_sentiment`)
  - `indicators/technical.py`: 퀀트 팩터 지표 추가 — `return_60d`(중기 모멘텀),
    `disparity_ema20`(이격도)
  - `agents/protocol.py`: `MarketContext.news_sentiment` 필드 추가
  - `agents/prompts/context_builder.py`: 신규 지표·감성 점수를 AI 프롬프트 텍스트에 반영
  - `tests/unit/test_sentiment.py`, `tests/unit/test_indicators.py`: 신규 단위 테스트

### Changed
- `data/data_manager.py::refresh_news()`: 신규 기사에 대해 본문 수집 + 감성 점수화 후 저장
  (기존 `fetch_article_body()`를 연결, `NewsArticle.sentiment_score` 컬럼을 처음으로 채움)
- `scheduler/tasks.py::run_analysis_for_ticker()`, `dashboard/pages/3_ai_debate.py`:
  뉴스 감성 점수 집계 후 `MarketContext`에 반영
- `docs/REQUIREMENTS.md`: A-09~A-12, D-11~D-12, F-07~F-09 추가 및 v1.1→v1.2 변경 이력 기록

### Added (AI 토론 세션 간 연속성, v1.2→v1.3)
- `agents/protocol.py`: `PriorSessionSummary` dataclass 신규, `MarketContext.prior_sessions` 필드 추가
- `agents/orchestrator.py`: `get_recent_sessions(ticker, limit=None)` — 동일 종목 최근 N개
  과거 토론 세션 + 마지막 라운드 근거를 조회 (`id` 내림차순, `created_at`보다 결정론적)
- `agents/prompts/context_builder.py`: `build_prior_sessions_text()` — `[과거 분석 이력]`
  섹션을 `build_market_context_text()`에 삽입 (Round 1~5 전체에 자동 전파, 프롬프트 빌더
  3개 파일은 수정 불필요)
- `config/settings.py`: `prior_sessions_limit` (기본 3) 추가
- `scheduler/tasks.py::run_analysis_for_ticker()`, `dashboard/pages/3_ai_debate.py`: 모든
  `MarketContext` 생성 지점에서 `get_recent_sessions()` 자동 호출
- `docs/AI_AGENT_PROTOCOL.md`: "세션 간 연속성 정책(Cross-Session Continuity Rule)" 신규 절
- `docs/REQUIREMENTS.md`: A-13 추가, v1.2→v1.3 변경 이력 기록
- `tests/unit/test_session_continuity.py`: 신규 단위 테스트 7개

### 예정 작업
- KIS OpenAPI 실거래 연동 (`data/kis_client.py` 완전 구현)
- KIS WebSocket 실시간 시세 수신
- 6개월 백테스트 스크립트 (`scripts/backtest.py`)
- DART 재무제표 연동(A-11/D-11), 수급 데이터 연동(A-12/D-12) — Alembic 초기화 선행 필요

## [1.1.0] — 2026-06-23

### Added
- **실시간·배치·수기 데이터 갱신 시스템**
  - `data/realtime_collector.py`: `DataRefreshManager` 싱글턴
    - 수기 즉시 갱신 (`refresh_now()`)
    - 분봉·시간봉 배치 갱신 (`refresh_intraday_batch()`)
    - AI 분석 콜백 등록 (`register_analysis_trigger()`)
    - 인메모리 가격 캐시 + 0.5% 이상 변화 감지 시 즉시 AI 재분석
  - `api/routes/refresh.py`: 수기 갱신 REST API
    - `POST /api/refresh/manual`: 비동기 수기 갱신
    - `POST /api/refresh/manual/sync`: 동기 수기 갱신
    - `POST /api/refresh/intraday`: 분봉·시간봉 갱신
    - `GET /api/refresh/prices`: 최신 가격 캐시 조회
    - `GET /api/refresh/status`: 종목별 마지막 갱신 시각
  - `dashboard/components/refresh_panel.py`: Streamlit 수기 갱신 UI
    - 데이터 유형 선택 (OHLCV/뉴스/분봉)
    - 갱신 후 AI 즉시 분석 토글
    - 사이드바 통합 (1_overview, 2_stock_analysis 페이지)
  - `scheduler/job_runner.py`: 장중 5분마다 `job_intraday_refresh` 추가
  - `scheduler/tasks.py`: `run_analysis_for_ticker()` 분리 (콜백으로 등록 가능)

### Changed
- `scheduler/tasks.py`: `job_news_refresh`가 뉴스 갱신 후 AI 재분석 자동 트리거
- `docs/REQUIREMENTS.md`: D-06~D-10 요구사항 추가 및 완료 표시

---

## [1.0.0] — 2026-06-23

### Added
- **프로젝트 최초 구현** (Phase 1-2 완료)

**데이터 레이어**
- `data/pykrx_client.py`: pykrx 기반 KOSPI 상위 10개 종목 OHLCV 수집
- `data/naver_scraper.py`: NAVER Finance 뉴스 헤드라인 스크래핑
- `data/data_manager.py`: 통합 수집·upsert 오케스트레이터
- `indicators/technical.py`: ta 라이브러리 기반 기술 지표 (RSI, MACD, BB, EMA, ATR 등)

**AI 에이전트**
- `agents/protocol.py`: 공유 데이터 구조 (MarketContext, AgentMessage, ConsensusResult, ExitReason)
- `agents/local_cli_runner.py`: subprocess 기반 로컬 claude/codex CLI 실행 + SDK 폴백
- `agents/orchestrator.py`: 적응형 토론 루프 (최대 5라운드, 6가지 수렴·중단 조건)
- `agents/prompts/`: 라운드별 프롬프트 템플릿 (초기 분석·검토·협상)

**거래 엔진**
- `trading/risk_manager.py`: 포지션 한도·손절·일일 손실 한도 강제
- `trading/paper_broker.py`: DB 기반 모의거래 시뮬레이터
- `trading/order_executor.py`: paper/live 라우팅 (KIS 연동은 Phase 3)
- `trading/portfolio.py`: 포트폴리오 상태 계산·스냅샷 저장

**스케줄러**
- `scheduler/tasks.py`: 장중 작업 정의 (08:50, 09:10, 15:40, 16:00 KST)
- `scheduler/job_runner.py`: APScheduler CronTrigger 등록

**대시보드 (Streamlit 5페이지)**
- `dashboard/pages/1_overview.py`: 포트폴리오 현황 + 자산 추이
- `dashboard/pages/2_stock_analysis.py`: 종목별 캔들차트 + 기술 지표
- `dashboard/pages/3_ai_debate.py`: AI 토론 라운드 뷰어
- `dashboard/pages/4_trade_log.py`: 매매 이력 + CSV 내보내기
- `dashboard/pages/5_settings.py`: 시스템 상태 + 설정

**기반 인프라**
- `core/models.py`: SQLAlchemy ORM 7개 테이블
- `core/database.py`: SQLite + WAL 모드 + context manager 세션
- `config/settings.py`: pydantic-settings 환경변수 로딩
- `scripts/setup_db.py`: DB 초기화 + 종목 마스터 적재
- `scripts/backfill_data.py`: 2년치 OHLCV 백필
- `start.bat`: Windows 원클릭 실행
- 단위 테스트 22개 (tests/unit/test_agents.py)

**문서**
- `CLAUDE.md`: Claude Code CLI 자동 로드 프로젝트 컨텍스트
- `README.md`: GitHub 메인 페이지
- `docs/REQUIREMENTS.md`: 요구사항 + 변경 이력
- `docs/ARCHITECTURE.md`: 시스템 아키텍처 + ADR
- `docs/DEVELOPMENT_RULES.md`: 개발 표준 룰 10개 항목
- `docs/AI_AGENT_PROTOCOL.md`: AI 토론 프로토콜 상세 명세
- `docs/SETUP_GUIDE.md`: 설치 및 실행 가이드
- `.claude/settings.json`: 프로젝트 자동 권한 설정

### Changed
- 프론트엔드 스택: React+Vite → **Streamlit** (Python 단일 스택 요구사항 반영)
- AI 실행 방식: SDK 직접 호출 → **로컬 CLI subprocess 실행** (SDK는 폴백)
- 토론 구조: 고정 3라운드 → **적응형 최대 5라운드 + 수렴 조기 종료**

### Fixed
- `_detect_oscillation()` 오실레이션 감지 로직: 에이전트별 개별 감지 → **전체 신호 시퀀스 교대 패턴 감지**로 수정 (단위 테스트로 검증)
