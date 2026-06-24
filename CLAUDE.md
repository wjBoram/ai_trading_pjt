# CLAUDE.md — 프로젝트 AI 컨텍스트

> 이 파일은 Claude Code CLI가 프로젝트 디렉토리 진입 시 **자동으로 읽는** 컨텍스트 파일입니다.
> Claude Code는 이 파일을 진입점으로 사용합니다. Codex 전용 규칙은 `AGENTS.md`,
> 두 도구의 공통 협업 절차는 `docs/CLAUDE_CODEX_WORKFLOW.md`를 기준으로 합니다.

---

## 프로젝트 개요

**국내주식(KOSPI/KOSDAQ 상위 10개) AI 자동매매 + Streamlit 대시보드**

- Claude Code CLI + Codex CLI 듀얼 AI 토론으로 매수/매도 신호 결정
- Python 단일 스택 (JS/TS 없음)
- 모의거래 기본값, KIS OpenAPI 실거래는 Phase 3 미구현
- 로컬 PC 단독 실행

**현재 구현 상태**: Phase 1-2 프로토타입. `docs/PROJECT_REVIEW_2026-06-24.md`의 P0/P1
수정과 검증이 우선이며, Phase 3 KIS OpenAPI 실거래는 아직 사용할 수 없습니다.

---

## 문서 구조 (먼저 읽어야 할 문서)

| 문서 | 내용 | 중요도 |
|------|------|--------|
| `AGENTS.md` | Codex 프로젝트 규칙 + 자동매매 안전 불변조건 | ★★★ |
| `docs/CLAUDE_CODEX_WORKFLOW.md` | Claude–Codex 작업 분담·handoff·교차 리뷰 | ★★★ |
| `docs/PROJECT_REVIEW_2026-06-24.md` | 현재 코드 위험·우선순위·수정 로드맵 | ★★★ |
| `docs/REQUIREMENTS.md` | 요구사항 전체 + 변경 이력 | ★★★ |
| `docs/ARCHITECTURE.md` | 시스템 구조 + ADR (설계 결정 이유) | ★★★ |
| `docs/DEVELOPMENT_RULES.md` | 코딩 표준 + 품질 규칙 | ★★★ |
| `docs/AI_AGENT_PROTOCOL.md` | AI 토론 프로토콜 상세 | ★★ |
| `docs/SETUP_GUIDE.md` | 설치·실행 방법 | ★★ |
| `docs/USER_GUIDE.md` | 대시보드·API·갱신 사용법 | ★★ |
| `docs/CHANGELOG.md` | 버전별 변경 내용 | ★ |

Claude와 Codex를 같은 작업에 사용할 때는 **한 에이전트만 구현 파일을 수정**하고 다른 에이전트는
read-only 리뷰어 역할을 맡습니다. 세부 절차와 handoff 형식은
`docs/CLAUDE_CODEX_WORKFLOW.md`를 따릅니다.

## 대화 컨텍스트 복원 (세션 이어하기)

이전 개발 대화를 이어서 작업할 때:

1. `conversations/SESSIONS.md` — 전체 세션 인덱스 확인
2. `conversations/sessions/<최신파일>.md` — 마지막 세션 상세 내용 확인
3. 미결 사항부터 작업 재개

> 새 Claude Code 세션 시작 시 위 두 파일을 자동으로 읽어달라고 요청하세요.

### 세션 종료 시 자동 기록 (SessionEnd 훅)

이 프로젝트 디렉토리에서 종료되는 모든 Claude Code 세션은 `.claude/settings.json`의
`SessionEnd` 훅(`scripts/auto_save_session.py`)에 의해 자동으로 기록됩니다. 사용자가
세션 종료 전에 별도로 저장을 요청하지 않아도 항상 다음이 수행됩니다:

1. **원본 로그 (항상 저장, 추가 비용 없음)**: transcript를 파싱해
   `conversations/auto/<날짜>_<시각>_<세션ID>.md` 에 사용자/Claude 턴을 그대로 기록.
2. **AI 큐레이션 요약 (최선 노력)**: `claude -p`를 한 번 더 호출해 읽기 좋은 한국어
   세션 로그를 생성, `conversations/sessions/<날짜>_<번호>.md` 에 저장하고
   `conversations/SESSIONS.md` 인덱스에 행 추가. 실패해도 1번 원본 로그는 남음.
3. 모든 결과는 `conversations/AUTO_LOG.md` 에 한 줄로 기록(성공/실패 여부 포함).

`conversations/sessions/` 에는 이렇게 자동 생성된 파일과, 기존처럼
`python scripts/save_context.py` + 수동 작성으로 만든 파일이 섞여 있을 수 있다.
`SESSIONS.md`의 "버전" 컬럼이 `auto`로 표시된 행은 자동 생성된 것이다.

---

## 핵심 파일 위치

```
agents/orchestrator.py      ← AI 토론 루프 핵심 (가장 중요)
agents/local_cli_runner.py  ← 로컬 CLI subprocess 실행
agents/protocol.py          ← 공유 데이터 구조 (Signal, ExitReason 등)
trading/risk_manager.py     ← 리스크 한도 강제 (절대 우회 불가)
core/models.py              ← DB 스키마 (단일 진실 원천)
config/settings.py          ← 모든 설정값 (MAX_ROUNDS, 리스크 한도 등)
data/kis_client.py          ← KIS API (Phase 3 구현 대상)
dashboard/pages/3_ai_debate.py  ← AI 토론 시각화 UI
scripts/auto_save_session.py    ← SessionEnd 훅: 세션 종료 시 대화 자동 기록
```

---

## 모듈 의존성 방향 (역방향 임포트 금지)

```
config → core → data → indicators → agents → trading → scheduler → api → dashboard
```

---

## 개발 시 반드시 따를 규칙 (요약)

> 전체 규칙: `docs/DEVELOPMENT_RULES.md`

1. **타입 힌트** 모든 함수에 필수
2. **`ruff check && ruff format`** 커밋 전 실행
3. **`get_session()` context manager**로만 DB 세션 사용 (수동 commit 금지)
4. **`structlog` 키워드 인자**로 로깅 (f-string 보간 금지, print 금지)
5. **`core.exceptions`** 커스텀 예외 사용 (bare except, 묵살 금지)
6. **`config/settings`**로만 환경변수 접근 (하드코딩·직접 `os.environ` 금지)
7. **새 기능 = 테스트 동반** (tests/unit/ 또는 tests/integration/)
8. **DB 스키마 변경 = Alembic 마이그레이션** 필수
9. **`docs/REQUIREMENTS.md`** 상태 업데이트 + **`docs/CHANGELOG.md`** 기록
10. **`TRADING_MODE=paper`** 기본값 유지 (live 전환은 명시적 요청 시에만)

---

## AI 토론 프로토콜 요약

```
Round 1: claude CLI → 초기 분석 (BUY/SELL/HOLD + 신뢰도)
Round 2: codex CLI → 검토 + 동의/반박
Round 3~5: 협상 (수렴 조건 충족 시 조기 종료)
종료 조건: 합의(B) | 신뢰도 하한(A/C) | 오실레이션(D) | 최대라운드(E) | 타임아웃(F)
```

---

## 자동 허용된 작업 (사용자 매번 확인 불필요)

> `.claude/settings.json`에 정의된 프로젝트 권한

- Python 파일 읽기·수정
- `python scripts/*.py` 실행 (setup_db, backfill_data 등)
- `python -m pytest tests/` 실행
- `ruff check && ruff format` 실행
- `pip install` (requirements.txt 기반)
- `streamlit run` (대시보드 시작)
- `python main.py` (FastAPI 서버 시작)
- Git 상태 확인 (`git status`, `git diff`, `git log`)
- `data_store/` 디렉토리 파일 읽기
- `docs/` 문서 파일 생성·수정

## 사용자 확인이 필요한 작업

- `git push` (원격 저장소 푸시)
- `git commit` (커밋 생성)
- `.env` 파일 수정 (비밀 정보 포함)
- `TRADING_MODE=live` 관련 코드 수정
- KIS 실거래 주문 실행 코드 활성화
- 기존 DB 스키마 변경 (ALTER TABLE 등)
- `requirements.txt` 패키지 추가/삭제
- 새 외부 API 연동 추가

---

## 환경 정보

| 항목 | 값 |
|------|-----|
| Python | 3.11+ (3.13 지원은 별도 검증 필요) |
| 주요 프레임워크 | FastAPI, Streamlit |
| DB | SQLite (data_store/trading.db) |
| AI CLI | claude (Claude Code), codex (OpenAI) |
| 플랫폼 | Windows 11 |
| 기본 거래 모드 | paper (모의거래) |

---

## 빠른 시작 명령

```bash
# 최초 초기화
python scripts/setup_db.py && python scripts/backfill_data.py

# 실행
start.bat   # Windows: FastAPI + Streamlit 동시 시작

# 테스트
python -m pytest tests/ -v

# 코드 품질
ruff check . && ruff format .
```
