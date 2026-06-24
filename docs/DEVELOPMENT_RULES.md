# 개발 표준 룰

> **모든 AI(Claude, Codex)와 사람 개발자가 코드를 작성할 때 반드시 따라야 하는 표준입니다.**
> 이 룰을 벗어난 코드는 병합 불가 (향후 PR 기반 병합 시 체크리스트 적용).

---

## 1. Python 코딩 표준

| 항목 | 규칙 |
|------|------|
| Python 버전 | 3.11 이상 (타입 힌트 전면 적용) |
| 포매터 | `ruff format` (black 호환, 줄 길이 100) |
| 린터 | `ruff check` (E, W, F, I, UP 규칙) |
| 타입 힌트 | 모든 함수 파라미터·반환값 필수. `Any` 사용 최소화 |
| 임포트 순서 | stdlib → 서드파티 → 내부 모듈 (ruff-I 자동 정렬) |
| 문자열 | f-string 우선. `%` 포매팅 금지 |
| 매직 넘버 | 코드 내 상수 직접 기입 금지 → `config/settings.py` 명명 상수로 |

---

## 2. 모듈 의존성 방향 (단방향, 역방향 금지)

```
config → (없음)
   ↓
core → config
   ↓
data → core, config
   ↓
indicators → data, core
   ↓
agents → indicators, data, core, config
   ↓
trading → agents, data, core, config
   ↓
scheduler → trading, agents, data, core
   ↓
api → trading, agents, data, core
   ↓
dashboard → api, trading, agents, data, indicators, core
```

**순환 임포트 절대 금지.** 위 방향의 역방향 임포트 발생 시 즉시 리팩토링.

---

## 3. 에러 처리 표준

```python
# ✅ 올바른 패턴
from core.exceptions import DataFetchError

def fetch_ohlcv(ticker: str) -> pd.DataFrame:
    try:
        ...
    except NetworkError as e:
        logger.error("OHLCV 수집 실패", ticker=ticker, error=str(e))
        raise DataFetchError(f"ticker={ticker}") from e

# ❌ 금지 패턴
except Exception:          # 포괄 catch 금지
    pass                   # 묵살 금지
except:                    # bare except 금지
    return None            # 오류 은닉 금지
```

**모든 외부 API 호출**: `tenacity.retry` 데코레이터 적용 (최대 3회, 지수 백오프)

---

## 4. 로깅 표준

```python
# ✅ 올바른 패턴 (structlog, 키워드 인자)
import structlog
logger = structlog.get_logger(__name__)

logger.info("AI 토론 시작", ticker="005930", round=1)
logger.warning("오실레이션 감지", ticker="005930", signals=["BUY","SELL","BUY"])
logger.error("CLI 타임아웃", agent="codex", timeout_sec=120)

# ❌ 금지 패턴
print("디버그")                    # print 사용 금지
logger.info(f"ticker={ticker}")    # f-string 보간 금지 (키워드 인자 사용)
logging.info("메시지")             # 직접 logging 모듈 사용 금지
```

**로그 레벨 기준**:
- `DEBUG`: 개발 중 상세 추적
- `INFO`: 정상 흐름 (API 호출, 라운드 완료 등)
- `WARNING`: 비정상이지만 복구 가능 (데이터 없음, 오실레이션 등)
- `ERROR`: 조치 필요 (CLI 오류, API 실패 등)
- `CRITICAL`: 즉각 중단 (거래 시스템 심각 오류)

**거래 이벤트** (매수·매도·AI 결론)는 `logs/trades.log`에도 별도 기록.

---

## 5. 데이터베이스 패턴

```python
# ✅ 올바른 세션 관리 (context manager)
from core.database import get_session

def save_trade(trade_data: dict) -> Trade:
    with get_session() as session:    # 자동 commit/rollback
        obj = Trade(**trade_data)
        session.add(obj)
        return obj

# ❌ 금지 패턴
session = SessionLocal()              # 수동 세션 생성 금지
session.commit()                      # 수동 commit 금지
session.query(...).filter(...)        # .first() 없이 반환 금지 (N+1 위험)
```

**추가 규칙**:
- 원시 SQL 금지 → SQLAlchemy ORM 또는 Core Expression 사용
- N+1 쿼리 방지: 관계 로딩은 `selectinload`/`joinedload` 명시
- DB 스키마 변경 시 반드시 Alembic 마이그레이션 파일 생성

---

## 6. 설정·비밀 관리

```python
# ✅ 올바른 패턴
from config.settings import settings
api_key = settings.anthropic_api_key

# ❌ 절대 금지
API_KEY = "sk-ant-xxxxx"             # 하드코딩 금지
os.environ.get("ANTHROPIC_API_KEY")  # 직접 환경변수 접근 금지
```

**규칙**:
- 모든 비밀 정보는 `.env`에만 존재 (`.gitignore` 적용)
- `.env.example`에 키 이름·설명만 포함 (값 없음), 반드시 커밋
- `config/settings.py`의 `Settings` 클래스를 통해서만 접근

---

## 7. AI 에이전트 코드 생성 룰

Claude Code CLI 및 Codex CLI가 코드를 생성할 때의 추가 제약:

| 항목 | 규칙 |
|------|------|
| 테스트 동반 | 새 함수 → `tests/` 대응 테스트 필수 |
| 주석 방침 | `# WHAT` 주석 금지. `# WHY` (비자명 이유)만 허용 |
| 변경 범위 | 요청 외 코드 자의적 수정 금지 |
| 보안 | SQL Injection·Command Injection·하드코딩 비밀 생성 금지 |
| 의존성 | 새 패키지 추가 시 `requirements.txt` 동시 업데이트 필수 |
| 브레이킹 체인지 | 공개 API 변경 시 마이그레이션·호환 레이어 제공 |
| 문서 | 새 기능 추가 시 `docs/REQUIREMENTS.md` 요구사항 테이블 업데이트 |

---

## 8. 테스트 표준

```
tests/
├── unit/          # 외부 의존성 없는 순수 로직 테스트
│   └── test_agents.py, test_indicators.py, test_risk_manager.py
├── integration/   # DB·pykrx·파일시스템 사용 테스트
└── conftest.py    # 공통 픽스처 (인메모리 SQLite, mock 응답)
```

**규칙**:
- 핵심 경로 (agents, trading, risk_manager) 커버리지 **80% 이상** 유지
- AI 에이전트 테스트: 실제 CLI 호출 금지 → `conftest.py` 픽스처로 모킹
- `pytest -x` (첫 실패 즉시 중단)로 빠른 피드백 원칙
- CI 실행 명령: `python -m pytest tests/ -v --cov=. --cov-report=term`

---

## 9. 커밋 메시지 규칙

```
<type>(<scope>): <제목>

type: feat | fix | refactor | test | docs | chore
scope: agents | trading | data | dashboard | config | core | indicators | scheduler

예시:
feat(agents): 오실레이션 감지 조기 종료 룰 추가
fix(trading): KIS API 토큰 만료 시 자동 갱신 버그 수정
test(agents): 최대 라운드 강제 종료 시나리오 테스트 추가
docs: REQUIREMENTS.md KIS 연동 상태 업데이트
```

**커밋 원칙**:
- 1 논리 변경 = 1 커밋 (거대 커밋 금지)
- `main` 브랜치 직접 푸시 금지
- 테스트 통과 후 커밋

---

## 10. 새 기능 추가 체크리스트

Pull Request 병합 전 아래 항목 **전체** 충족 필요:

- [ ] 기존 도메인 구조 내 적절한 위치에 파일 배치
- [ ] 타입 힌트 완비
- [ ] `ruff check && ruff format` 통과
- [ ] `pytest` 통과 (커버리지 유지)
- [ ] `.env.example` 업데이트 (새 환경변수가 있는 경우)
- [ ] 에러 처리 및 structlog 로깅 구현
- [ ] DB 변경 시 Alembic 마이그레이션 파일 포함
- [ ] `docs/REQUIREMENTS.md` 요구사항 항목 상태 업데이트
- [ ] `docs/CHANGELOG.md` 변경 내용 기록
