# 시스템 아키텍처

## 전체 구조

```
┌─────────────────────────────────────────────────────────────────────┐
│                         외부 데이터 소스                              │
│  pykrx (OHLCV)   KIS OpenAPI (실시간·주문)   NAVER Finance (뉴스)    │
└───────┬──────────────────┬──────────────────────┬───────────────────┘
        ↓                  ↓                      ↓
┌───────────────────────────────────────────────────────────────────┐
│                  데이터 수집 레이어 (APScheduler)                   │
│  data/pykrx_client.py  data/kis_client.py  data/naver_scraper.py  │
│  data/data_manager.py (통합 오케스트레이터)                         │
└───────────────────────────┬───────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────────┐
│                     SQLite 데이터베이스                             │
│  stocks | ohlcv_daily | news_articles | agent_sessions             │
│  agent_rounds | positions | trades | portfolio_snapshots           │
└──────────────┬────────────────────────────────────────────────────┘
               ↓
    ┌──────────┴──────────┐
    ↓                     ↓
┌──────────────┐   ┌────────────────────────────────────────┐
│ indicators/  │   │         agents/orchestrator.py          │
│ technical.py │   │  (적응형 토론 루프, 수렴·중단 조건)       │
│ RSI·MACD·BB  │→  │                                        │
│ EMA·ATR 등   │   │  Round 1: agents/local_cli_runner.py   │
└──────────────┘   │    → subprocess: claude CLI            │
                   │  Round 2: local_cli_runner.py          │
                   │    → subprocess: codex CLI             │
                   │  Round 3~5: 협상 (수렴 시 조기 종료)    │
                   │  합의 계산 → ConsensusResult           │
                   └────────────────┬───────────────────────┘
                                    ↓
                   ┌────────────────────────────────────────┐
                   │           trading/risk_manager.py       │
                   │  (포지션 한도·손절·일일 한도 강제 검증)   │
                   └──────────────┬─────────────────────────┘
                                  ↓
                    ┌─────────────┴────────────┐
                    ↓                          ↓
         ┌──────────────────┐     ┌────────────────────────┐
         │ trading/         │     │ trading/               │
         │ paper_broker.py  │     │ order_executor.py (KIS) │
         │ (기본·안전)       │     │ (Phase 3 이후 활성화)   │
         └────────┬─────────┘     └──────────┬─────────────┘
                  └──────────┬────────────────┘
                             ↓
                   ┌────────────────────┐
                   │ Streamlit Dashboard │
                   │  :8501             │
                   ├────────────────────┤
                   │ FastAPI REST API   │
                   │  :8000             │
                   └────────────────────┘
```

---

## AI 듀얼 에이전트 토론 프로토콜

### 수렴·중단 조건 (6가지)

```
MarketContext 준비 (OHLCV 20일 + 지표 + 뉴스)
        ↓
Round 1: claude CLI (초기 분석)
        ↓ [조건 A 평가: claude confidence < MIN_CONF → HOLD 강제 종료]
Round 2: codex CLI (검토)
        ↓ [조건 B: 신호 일치 + avg_conf ≥ 0.65 → 합의 즉시 종료]
          [조건 C: codex confidence < MIN_CONF → HOLD 강제 종료]
Round 3~5: 협상 (홀수=claude, 짝수=codex)
        ↓ 각 라운드 후:
          [조건 B: 합의 달성]
          [조건 D: 오실레이션 (BUY→SELL→BUY 교대) → HOLD 강제]
          [조건 E: round ≥ MAX_ROUNDS(5) → 가중 평균으로 결론]
          [조건 F: subprocess timeout → HOLD 강제]
```

### 가중 합의 점수

- BUY=+1, HOLD=0, SELL=-1
- 최신 라운드에 높은 가중치 (지수 감쇠)
- BUY if score ≥ +0.35 / SELL if score ≤ -0.35 / 나머지 HOLD
- `execute_trade = 합의 종료(B) AND avg_conf ≥ 0.65 AND risk_manager 승인`

---

## 로컬 CLI 실행 방식

```python
# agents/local_cli_runner.py
subprocess.run(["claude", "--print", "--output-format", "text"], input=prompt, ...)
subprocess.run(["codex", "--quiet"], input=prompt, ...)
```

CLI 미설치 시 자동 폴백:
- `claude` CLI 없음 → Anthropic SDK (`anthropic` 패키지)
- `codex` CLI 없음 → OpenAI SDK (`openai` 패키지)

---

## 데이터베이스 스키마 (7개 테이블)

| 테이블 | 핵심 컬럼 |
|--------|-----------|
| `stocks` | ticker (PK), name, market, is_active |
| `ohlcv_daily` | ticker+date (UQ), open, high, low, close, volume |
| `news_articles` | ticker, title, published_at, sentiment_score |
| `agent_sessions` | ticker, session_date, final_signal, weighted_score, exit_reason |
| `agent_rounds` | session_id (FK), round_number, agent, signal, confidence, reasoning |
| `positions` | ticker, quantity, avg_cost, paper (모의/실거래 구분) |
| `trades` | ticker, side, quantity, price, pnl, paper, ai_signal, ai_confidence |
| `portfolio_snapshots` | snapshot_date (UQ), total_value, cash, daily_pnl |

---

## 스케줄러 작업 (KST 기준, 평일만)

| 시각 | 작업 | 파일 |
|------|------|------|
| 08:50 | 전일 OHLCV + 지표 갱신 | `scheduler/tasks.py::job_premarket_data` |
| 09:10 | AI 토론 + 매매 신호 + 주문 실행 | `scheduler/tasks.py::job_morning_analysis` |
| 15:40 | 포트폴리오 스냅샷 저장 | `scheduler/tasks.py::job_eod_snapshot` |
| 16:00 | NAVER 뉴스 수집 | `scheduler/tasks.py::job_news_refresh` |

---

## 주요 설계 결정 (ADR)

### ADR-01: Streamlit 선택 (vs React)
- **결정**: Streamlit
- **이유**: Python 단일 스택 요구사항. 금융 대시보드에 Plotly 차트 내장, 빠른 개발.
- **트레이드오프**: 실시간 WebSocket push 불가 → 30초 polling으로 대체

### ADR-02: 로컬 CLI subprocess 실행 (vs SDK 직접 호출)
- **결정**: subprocess로 `claude`/`codex` CLI 실행, SDK는 폴백
- **이유**: "로컬 PC에 설치된 AI를 통해 소통" 요구사항. CLI가 설치된 환경에서는 인증·컨텍스트 관리를 CLI가 담당.
- **트레이드오프**: CLI 설치 전제조건 추가, 응답 파싱 복잡성 증가

### ADR-03: 적응형 라운드 (vs 고정 3라운드)
- **결정**: 최대 5라운드, 수렴 시 조기 종료
- **이유**: "무한루프 방지, 협의점 찾아 종료" 요구사항. 2라운드 합의 시 비용·시간 절약.
- **트레이드오프**: 라운드 수 예측 불가 → MAX_ROUNDS 설정으로 상한 보장

### ADR-04: SQLite (vs PostgreSQL)
- **결정**: SQLite (로컬), SQLAlchemy ORM으로 추상화
- **이유**: 로컬 단독 실행, 외부 DB 서버 불필요
- **트레이드오프**: 동시 쓰기 성능 제한 → WAL 모드로 완화. PostgreSQL 전환 시 DB_URL만 변경.
