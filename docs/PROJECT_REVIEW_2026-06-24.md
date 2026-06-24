# 프로젝트 코드 리뷰 및 최적화 로드맵

검토 기준일: 2026-06-24  
검토 범위: 애플리케이션 소스, 설정, 테스트, 문서, Claude/Codex CLI 연결부  
검토 방식: 정적 코드 리뷰와 로컬 CLI help 확인. Python 실행 환경 문제로 테스트와 ruff는 재실행하지 못함.

## 결론

현재 프로젝트는 “기술지표와 뉴스 컨텍스트를 LLM에 전달하고 결과를 paper DB에 기록하는 프로토타입”이다.
검증된 주가 예측 시스템이나 실거래 준비 완료 시스템으로 보기는 어렵다. 가장 먼저 CLI 연결, paper 회계,
DB 세션 수명, 데이터 시각 의미를 바로잡고, 주문 실행을 시장시간·멱등성·동시성 게이트 뒤로 옮겨야 한다.

`TRADING_MODE=live`는 활성화하면 안 된다. KIS 클라이언트가 없고 실거래 주문 함수가 미구현이며,
실시간 포지션 조회·주문 reconciliation·kill switch도 없다.

## 잘 구성된 기반

- 모듈이 `config/core/data/indicators/agents/trading/scheduler/api/dashboard`로 나뉘어 있다.
- 기본 거래 모드가 paper이고 주문 전에 별도 RiskManager를 호출하는 방향은 적절하다.
- AI 라운드 결과와 최종 결과를 DB에 남기는 구조가 있어 감사 추적의 출발점이 있다.
- 토론 파싱, 합의/오실레이션, 일부 지표와 세션 연속성에 대한 단위 테스트가 있다.
- 설정과 비밀값을 `.env`로 분리하고 구조화 로깅을 사용한다.

다만 이 기반이 실제 안전성을 보장하는 것은 아니며 아래 finding이 우선한다.

## Findings

### P0 — 즉시 차단/수정

#### P0-1. Codex CLI 호출이 현재 설치 버전과 맞지 않아 듀얼 에이전트가 동작하지 않는다

- 근거: `agents/local_cli_runner.py::run_codex_cli()`가 `codex --quiet`을 실행한다.
- 로컬 `codex.cmd --help`에는 `--quiet` 옵션이 없고 비대화형 인터페이스는 `codex exec`이다.
- CLI가 설치되어 있으므로 SDK fallback도 선택되지 않고, invalid option 오류가 라운드 실패로 끝난다.
- 방향: `codex exec` + stdin, sandbox/approval 정책, 출력 schema를 명시하고 subprocess contract test를
  추가한다. CLI 버전과 실제 argv를 진단 화면에 표시한다.

#### P0-2. 개발용 AI CLI가 비신뢰 시장 텍스트를 도구 권한과 함께 처리한다

- Claude 호출은 `--print`만 사용하며 shell/file 도구를 명시적으로 끄지 않는다. 현재 프로젝트의
  `.claude/settings.json`에는 일부 Bash 명령이 allow되어 있다.
- Codex를 `codex exec`로 고칠 때도 격리하지 않으면 coding agent가 저장소와 도구를 사용할 수 있다.
- 뉴스/과거 reasoning은 외부 비신뢰 텍스트이므로 prompt injection이 개발 도구 실행으로 확대될 수 있다.
- 방향: 런타임 시장 추론은 tool-free API + structured output을 우선한다. CLI 요구사항을 유지한다면
  빈 작업 디렉터리, 도구 비활성화/read-only sandbox, ephemeral session, project hook/rule 비활성화,
  출력 schema를 함께 적용한다. 개발 협업용 CLI 세션과 런타임 추론 프로세스를 분리한다.

#### P0-3. 데이터 갱신·분석과 주문 실행이 분리되지 않아 장외·중복 주문이 가능하다

- 근거: `scheduler/tasks.py::run_analysis_for_ticker()`는 분석 결과의 `execute_trade`가 참이면 호출 사유와
  시장시간에 관계없이 `execute_signal()`을 호출한다.
- `job_news_refresh()`는 16:00 KST에 전 종목 분석 후 같은 경로를 탄다.
- 수기 refresh API/UI도 분석 thread를 시작하며 같은 종목에 대한 실행 잠금이나 멱등키가 없다.
- 영향: after-hours 가격으로 paper 체결, 향후 live에서는 중복/장외 주문 위험이 있다.
- 방향: `analyze -> persist signal -> authorize order -> execute`를 분리한다. 주문 단계에 거래일/시장시간,
  quote freshness, idempotency key, 종목별 lock, 최신 계좌 상태 재검증을 둔다.

#### P0-4. 실시간·분봉 구현과 문서의 완료 표시가 실제 동작과 일치하지 않는다

- `data/pykrx_client.py::get_current_price()`는 당일 OHLCV의 종가를 조회하며 실시간 quote 계약이 아니다.
- `DataRefreshManager.refresh_intraday_batch()`는 전달받은 interval을 사용해 candle을 수집/저장하지 않고
  위 현재가 함수만 반복 호출한다.
- `fetch_intraday_ohlcv()`도 종목 단면의 한 행을 반환하는 구조이고 intraday 저장 테이블이 없다.
- 영향: stale/종가 데이터를 현재가·분봉으로 오인하고 AI 또는 주문 가격에 사용한다.
- 방향: KIS quote/WebSocket 어댑터와 별도의 intraday schema를 구현하기 전 D-04/D-06/D-07/D-10을
  완료로 표시하지 않는다. quote에 `as_of`, source, interval, stale 여부를 필수로 둔다.

#### P0-5. live 경로는 미구현인데 설정 하나로 진입할 수 있다

- `data/kis_client.py`가 없고 `_kis_buy/_kis_sell()`은 `NotImplementedError`다.
- live 모드에서 `_execute_sell()`과 stop-loss는 positions를 빈 배열로 두어 매도 경로에 도달하지 못한다.
- 방향: 현재는 설정 validation에서 live를 명시적으로 거부한다. 구현 후에도 계좌 조회, 주문 상태 전이,
  체결 reconciliation, idempotency, kill switch, sandbox 검증, 수동 승인 gate를 통과해야 활성화한다.

### P1 — 다음 기능 개발 전 수정

#### P1-1. PaperBroker 현금을 이중 차감한다

- `PaperBroker.get_cash()`의 `_calc_cash_from_trades()`가 이미 BUY 금액을 차감하는데 보유 포지션 원가를
  다시 뺀다.
- 예: 초기 1,000만원에서 100만원 매수 시 기대 현금은 900만원이지만 현재 계산은 800만원이다.
- `trading/portfolio.py`의 계산과도 서로 다르다.
- 방향: 단일 원장 계산 함수를 만들고 buy/sell/부분매도/연속매수 회귀 테스트를 추가한다.

#### P1-2. ORM 객체 수명 때문에 데이터가 있을 때 대시보드와 Trade 반환이 실패할 수 있다

- `SessionLocal`은 기본 `expire_on_commit=True`이고 `get_session()`은 read query도 commit한다.
- dashboard 2/3/4 페이지는 ORM 객체를 context 밖에서 읽는다.
- `PaperBroker.buy()/sell()`도 commit/close 후 ORM `Trade`를 반환한다.
- 영향: `DetachedInstanceError` 가능성이 높다.
- 방향: 경계 밖으로 DTO/dict만 반환하는 것을 기본으로 하고 transaction 정책을 명확히 한다.
  단순히 `expire_on_commit=False`로 가리는 경우에도 세션 경계 테스트를 추가한다.

#### P1-3. Dashboard가 DB에 없는 `AgentRound.signal_changed`를 읽는다

- `dashboard/pages/3_ai_debate.py`는 `r.signal_changed`를 사용하지만 `core/models.py::AgentRound`에 해당
  Column이 없다. 프로토콜 dataclass에는 있으나 저장도 하지 않는다.
- 방향: migration과 저장 로직을 포함해 필드를 추가하거나 UI에서 제거한다.

#### P1-4. 리스크 한도가 누적 포지션과 잘못된 입력을 막지 못한다

- 종목 비중은 기존 보유분을 제외한 신규 주문액만 검사해 반복 매수로 한도를 넘을 수 있다.
- 최대 종목 수에 도달하면 기존 종목 추가 매수도 무조건 거부한다.
- quantity/price/confidence의 유한성·양수·범위 검증이 없다.
- 일일 손실은 실현손익만 사용하며 미실현 손실과 일중 기준자산을 반영하지 않는다.
- stop-loss 함수는 정의되어 있으나 스케줄러/quote update에서 호출되는 경로가 확인되지 않는다.
- 방향: 주문 후 예상 상태를 입력으로 한 순수 risk decision을 만들고 경계값/property 테스트를 추가한다.

#### P1-5. AI 응답 검증이 느슨하고 외부 텍스트를 신뢰 경계 없이 프롬프트에 삽입한다

- confidence가 0~1인지, NaN/Infinity가 아닌지 검증하지 않는다.
- 배열 필드에 문자열이 오면 문자 배열로 변환될 수 있다.
- 뉴스 제목, 기사 본문에서 계산한 내용, 과거 reasoning을 명령과 구분하지 않고 프롬프트에 삽입한다.
- AI 자체 신뢰도를 포지션 크기와 거래 승인에 직접 사용한다.
- 방향: 두 CLI의 structured output 기능과 Pydantic schema를 사용하고, 외부 텍스트를 untrusted data로
  명시·구획한다. 포지션 크기는 검증된 전략 risk budget이 결정하고 AI confidence는 보조 입력으로만 쓴다.

#### P1-6. Round 1/2 타임아웃이 문서의 fail-closed 결과로 저장되지 않는다

- timeout catch는 협상 라운드(3+)에만 있다. Round 1/2의 `AgentTimeoutError`는 `run_debate()` 밖으로
  전파되어 scheduler의 광범위한 except에서 로그만 남고 세션도 저장되지 않는다.
- 방향: 모든 라운드를 같은 상태 머신으로 실행하고 TIMEOUT/CLI_ERROR 결과와 원인을 저장한다.

#### P1-7. 상태 변경 API가 인증 없이 외부 인터페이스에 노출된다

- FastAPI는 `0.0.0.0:8000`에 바인딩되고 refresh POST는 인증 없이 AI 분석과 거래 경로를 촉발할 수 있다.
- CORS는 인증/접근제어가 아니다.
- 방향: 기본 bind를 `127.0.0.1`로 제한하고 mutation endpoint 인증, CSRF/토큰, 입력 ticker/data_type
  allowlist, rate limit를 추가한다. live에서는 API가 직접 주문을 촉발하지 못하게 한다.

#### P1-8. 스케줄러가 휴장일과 다중 프로세스 중복 실행을 처리하지 않는다

- `is_market_open()`은 평일과 시각만 검사해 공휴일/임시휴장을 모른다.
- scheduler는 FastAPI lifespan에 결합되어 reload 또는 복수 worker에서 중복 시작될 수 있다.
- `main.py`의 직접 실행은 `reload=True`다.
- 방향: 거래소 캘린더, 독립 scheduler process 또는 leader lock, persistent job/idempotency를 도입한다.

### P2 — 구조와 품질 개선

#### P2-1. 테스트 포트폴리오가 핵심 위험 경로를 다루지 않는다

- 현재 수집된 테스트 함수는 약 42개지만 `tests/integration/`은 비어 있다.
- broker 회계, order executor, scheduler 중복, API 인증/검증, ORM session 수명, CLI subprocess argv,
  데이터 stale 처리 테스트가 없다.
- 요구사항의 80%+ coverage 상태를 뒷받침하는 실행 결과나 CI가 없다.
- 방향: P0/P1마다 실패 재현 테스트를 먼저 만들고, coverage threshold를 CI에서 강제한다.

#### P2-2. 예측 성능을 평가할 데이터 모델과 백테스트가 없다

- 현재 결과는 LLM 판단 신호이며 예측 target/horizon, 실제 수익 결과, benchmark, calibration을 저장하지 않는다.
- `scripts/backtest.py`도 없다.
- 방향: prediction/decision/order/fill을 별도 엔터티로 분리하고, 다음 거래일 수익률과 비용 반영 성과를
  사후 결합한다. 단순 전략과 비교한 walk-forward 평가를 통과하기 전 자동매매 효과를 주장하지 않는다.

#### P2-3. 스키마 migration 체계가 선언만 되어 있다

- requirements에는 Alembic이 있지만 설정/versions 디렉터리가 없고 시작 시 `create_all()`만 실행한다.
- 방향: baseline migration, schema version check, backup/restore 절차를 추가한다.

#### P2-4. 환경과 문서가 서로 다르다

- README는 Python 3.11+, CLAUDE 문맥은 Python 3.13, ruff target은 py311이다.
- README의 AI 모델명은 코드의 fallback/실제 CLI 기본 모델과 결합되어 빠르게 낡는다.
- requirements 일부는 exact pin이고 일부는 unpinned라 재현성이 불완전하다.
- 방향: 지원 Python 버전과 lock 전략을 하나로 정하고 CI matrix로 검증한다. CLI 모델은 하드코딩보다
  설정·실행 메타데이터로 기록한다.

#### P2-5. 저장소 위생과 세션 자동저장 경로 문제가 있다

- 현재 경로에서 `git status`는 “not a git repository”로 실패했다.
- 루트에 `dstock_pjt_aiconversations*` 디렉터리가 있어 Windows 절대경로 정규화 오류 흔적이 있다.
- 캐시와 pyc 파일도 작업 트리에 존재한다.
- 방향: 사용자 확인 후 Git을 초기화/연결하고, 잘못 생성된 디렉터리의 내용을 확인해 보존 또는 정리한다.
  `auto_save_session.py`에는 Windows 경로 회귀 테스트를 추가한다.

## 권장 수정 순서

### Gate 0 — 안전 동결

- live 설정을 애플리케이션 시작 시 거부한다.
- 분석과 주문 실행을 분리하고 장외/수기 refresh의 자동 주문을 중단한다.
- Git 저장소와 Python 실행 환경을 정상화한다.
- 요구사항의 과도한 “완료” 표시를 실제 상태로 정정한다.

완료 기준: 어떤 API/스케줄러/AI 실패도 외부 주문으로 이어지지 않으며 모든 실행은 paper로 식별된다.

### Phase 1 — 결정론적 정확성

- Codex argv, tool-free 격리, timeout 상태 머신, strict response schema 수정
- paper cash/position 원장과 ORM DTO 경계 수정
- dashboard schema 불일치 수정
- risk input 및 주문 후 비중 검증
- 각 항목 회귀 테스트와 CI 추가

완료 기준: lint/format/test가 깨끗하고 핵심 회계·위험 경로 테스트가 실제 결함을 재현한 뒤 통과한다.

### Phase 2 — 데이터/실행 아키텍처

- Quote/Candle provider interface와 KIS sandbox adapter
- 데이터 provenance/freshness, 거래소 캘린더
- analysis/decision/order/fill 상태 모델
- per-ticker lock, order idempotency, scheduler leader lock
- API 인증과 localhost 기본 bind

완료 기준: 공급자 장애·중복 job·프로세스 재시작 테스트에서도 주문 상태가 일관된다.

### Phase 3 — 예측 평가와 paper 검증

- target/horizon이 명시된 prediction 저장
- 비용 포함 walk-forward backtest와 baseline 비교
- 신뢰도 calibration 및 전략 risk budget
- 최소 수 주 이상의 shadow/paper 운영과 운영 지표

완료 기준: 재현 가능한 평가 보고서, 최대 손실/회전율/슬리피지 포함 성과, 데이터 누수 점검이 있다.

### Phase 4 — 제한적 live readiness

- KIS sandbox end-to-end, 계좌/체결 reconciliation
- kill switch, 일일 손실 circuit breaker, 수동 승인, 알림/감사로그
- 소액 canary와 rollback runbook
- 보안 검토와 장애 훈련

완료 기준: 별도 live-readiness 체크리스트를 사람이 승인하기 전에는 live flag를 열지 않는다.

## 검증 상태

- 성공: 저장소 파일 정적 검토, `codex.cmd --help`, `codex.cmd exec --help`, `claude.cmd --help`
- 실패: `python -m pytest tests -q`, `python -m ruff check .`
- 실패 원인: 현재 `python`이 WindowsApps alias(`python.exe` 0.0.0.0)를 가리키며 “logon session does not
  exist” 오류로 실행되지 않았다. `ruff` standalone 명령도 PATH에 없다.
- 따라서 기존 pycache/pytest cache가 있어도 이번 리뷰에서 테스트 통과를 확인했다고 간주하지 않는다.
