# 국내주식 AI 자동매매 시스템

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39-red.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

KOSPI/KOSDAQ 상위 10개 종목을 대상으로 **Claude Code CLI + Codex CLI 듀얼 AI 토론**을 통해
최적 매수/매도를 자동 결정하는 시스템. Streamlit 웹 대시보드로 투자 현황 실시간 모니터링.

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| 📊 **데이터 수집** | pykrx(일봉/분봉/시간봉), KIS 실시간, NAVER 뉴스 |
| 🤖 **듀얼 AI 토론** | Claude ↔ Codex 적응형 토론 (최대 5라운드, 합의 시 조기 종료) |
| 🔄 **즉시·배치 갱신** | 자동 스케줄 + 수기 갱신 + 갱신 즉시 AI 분석 트리거 |
| 💹 **자동 매매** | 모의거래(기본), KIS OpenAPI 실거래는 Phase 3 예정 |
| 🛡️ **리스크 관리** | 손절(-5%), 종목당 최대 비중(20%), 일일 손실 한도(-3%) |
| 📈 **웹 대시보드** | 포트폴리오·캔들차트·AI 토론 뷰어·매매 이력 |

---

## 시스템 아키텍처

```
외부 데이터 (pykrx / KIS / NAVER)
        ↓
데이터 수집 레이어 (배치 + 수기 갱신)
        ↓
SQLite DB (OHLCV·뉴스·포지션·토론 이력)
        ↓
AI 분석 엔진 (Claude CLI ↔ Codex CLI 토론)
        ↓
거래 엔진 (리스크 관리 → 모의/실거래)
        ↓
Streamlit 대시보드 (:8501)
```

---

## 빠른 시작

### 1. 설치

```bash
git clone https://github.com/<your-username>/stock_pjt_ai.git
cd stock_pjt_ai
pip install -r requirements.txt

# AI CLI 설치
npm install -g @anthropic-ai/claude-code
npm install -g @openai/codex
```

### 2. 환경 설정

```bash
cp .env.example .env
# .env 파일에 API 키 입력
```

### 3. 초기화 및 실행

```bash
python scripts/setup_db.py       # DB 초기화
python scripts/backfill_data.py  # 2년치 데이터 수집
start.bat                         # 대시보드 시작
```

→ **대시보드**: `http://localhost:8501`

---

## AI 토론 프로토콜

```
Round 1: Claude CLI — 기술적 분석 초기 판단
Round 2: Codex CLI  — 독립 검토 + 반박
Round 3~5: 협상     — 수렴 시 즉시 종료

종료 조건:
  B. 합의 달성 (동일 신호 + 신뢰도 ≥ 65%)
  A/C. 신뢰도 하한 미달 → HOLD 강제
  D. 오실레이션 감지 → HOLD 강제
  E. 최대 5라운드 → 가중 평균 결론
  F. 타임아웃 → HOLD 강제
```

---

## 데이터 갱신 방식

| 방식 | 대상 | 트리거 |
|------|------|--------|
| **자동 배치** | 일봉·뉴스 | APScheduler (08:50, 09:10, 16:00 KST) |
| **실시간 배치** | 분봉·시간봉 | 장중 N분마다 자동 |
| **수기 갱신** | 모든 데이터 | 대시보드 버튼 / REST API |
| **갱신 → 즉시 분석** | AI 토론 재실행 | 데이터 갱신 후 자동 트리거 |

---

## 프로젝트 문서

| 문서 | 설명 |
|------|------|
| [CLAUDE.md](CLAUDE.md) | AI 프로젝트 컨텍스트 (Claude Code 자동 로드) |
| [AGENTS.md](AGENTS.md) | Codex 프로젝트 규칙 및 자동매매 안전 기준 |
| [docs/CLAUDE_CODEX_WORKFLOW.md](docs/CLAUDE_CODEX_WORKFLOW.md) | Claude–Codex 협업·handoff·교차 리뷰 절차 |
| [docs/PROJECT_REVIEW_2026-06-24.md](docs/PROJECT_REVIEW_2026-06-24.md) | 현재 코드 리뷰와 우선순위별 수정 로드맵 |
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | 요구사항 + 변경 이력 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 시스템 아키텍처 + 설계 결정 |
| [docs/DEVELOPMENT_RULES.md](docs/DEVELOPMENT_RULES.md) | 개발 표준 룰 |
| [docs/AI_AGENT_PROTOCOL.md](docs/AI_AGENT_PROTOCOL.md) | AI 토론 프로토콜 상세 |
| [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) | 설치·실행 가이드 |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | 버전별 변경 이력 |

---

## 디렉토리 구조

```
stock_pjt_ai/
├── CLAUDE.md                  # AI 컨텍스트 (Claude Code 자동 로드)
├── .claude/settings.json      # 프로젝트 자동 권한 설정
├── config/                    # 설정 (settings.py, logging_config.py)
├── core/                      # DB 모델·세션·스키마·예외
├── data/                      # 데이터 수집 (pykrx, KIS, NAVER)
├── indicators/                # 기술적 지표 계산
├── agents/                    # AI 에이전트 (orchestrator, prompts)
├── trading/                   # 거래 엔진 (risk, paper, executor)
├── scheduler/                 # APScheduler 작업
├── api/                       # FastAPI REST 엔드포인트
├── dashboard/                 # Streamlit 대시보드
├── scripts/                   # 초기화·백필·백테스트
├── tests/                     # 단위·통합 테스트
└── docs/                      # 프로젝트 문서
```

---

## 기술 스택

- **언어**: Python 3.11+ (단일 스택)
- **대시보드**: Streamlit + Plotly
- **백엔드**: FastAPI + uvicorn
- **DB**: SQLite + SQLAlchemy
- **데이터**: pykrx, KIS OpenAPI, NAVER Finance
- **AI**: Claude Code CLI (claude-sonnet-4-6) + Codex CLI (GPT-4o)
- **스케줄러**: APScheduler

---

## 주의사항

- `TRADING_MODE=paper` (모의거래)가 기본값입니다
- `live` 전환 전 반드시 KIS 샌드박스에서 충분히 테스트하세요
- KIS OpenAPI 신청 후 승인까지 1~3 영업일 소요
