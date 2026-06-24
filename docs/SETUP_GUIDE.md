# 설치 및 실행 가이드

## 전제 조건

| 항목 | 최소 버전 | 확인 명령 |
|------|---------|---------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| Claude Code CLI | 최신 | `claude --version` |
| Codex CLI | 최신 | `codex --version` |

---

## 1. 초기 설치

### 1-1. 프로젝트 클론

```bash
git clone https://github.com/<your-username>/stock_pjt_ai.git
cd stock_pjt_ai
```

### 1-2. Python 패키지 설치

```bash
pip install -r requirements.txt
```

### 1-3. AI CLI 설치 (최초 1회)

```bash
# Claude Code CLI
npm install -g @anthropic-ai/claude-code

# OpenAI Codex CLI
npm install -g @openai/codex
```

### 1-4. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 에디터로 열어 아래 항목 입력:
```

| 환경 변수 | 설명 | 필수 |
|---------|------|------|
| `KIS_APP_KEY` | KIS OpenAPI App Key | Phase 3부터 |
| `KIS_APP_SECRET` | KIS OpenAPI App Secret | Phase 3부터 |
| `KIS_ACCOUNT_NUMBER` | 계좌번호 | Phase 3부터 |
| `ANTHROPIC_API_KEY` | Claude API (CLI 폴백용) | 권장 |
| `OPENAI_API_KEY` | OpenAI API (CLI 폴백용) | 권장 |
| `TRADING_MODE` | `paper` (기본) 또는 `live` | 필수 |

---

## 2. DB 초기화 (최초 1회)

```bash
# 테이블 생성 + 종목 마스터 적재
python scripts/setup_db.py

# 2년치 OHLCV 백필 (5~10분 소요)
python scripts/backfill_data.py
```

---

## 3. 실행

### 원클릭 실행 (Windows)

```bat
start.bat
```

- FastAPI: `http://localhost:8000/docs`
- Streamlit: `http://localhost:8501`

### 개별 실행

```bash
# FastAPI 백엔드
python main.py

# Streamlit 대시보드 (별도 터미널)
streamlit run streamlit_app.py --server.port 8501
```

---

## 4. KIS OpenAPI 신청 절차 (실거래 시 필요)

1. [한국투자증권](https://www.koreainvestment.com) 계좌 개설
2. `온라인지점 → 서비스 신청 → OpenAPI` 메뉴에서 신청
3. 승인 완료 (1~3 영업일) 후 App Key / App Secret 발급
4. `.env` 파일에 입력
5. **샌드박스 테스트**: `KIS_BASE_URL=https://openapivts.koreainvestment.com:9443`
6. **실거래 전환**: `KIS_BASE_URL=https://openapi.koreainvestment.com:9443` + `TRADING_MODE=live`

> ⚠️ `TRADING_MODE=live`는 실제 자금이 투입됩니다. 반드시 샌드박스에서 충분히 테스트 후 전환하세요.

---

## 5. AI 분석 수동 실행

대시보드 → **🤖 AI Debate** 페이지 → 종목 선택 → **AI 분석 실행** 버튼

또는 Python 직접 실행:

```python
from agents.orchestrator import run_debate, save_session_to_db
from agents.protocol import MarketContext
from data.data_manager import get_recent_ohlcv, get_recent_news
from data.pykrx_client import get_current_price
from indicators.technical import get_latest_indicators

ticker = "005930"
df = get_recent_ohlcv(ticker, days=60)
indicators = get_latest_indicators(df)
ctx = MarketContext(
    ticker=ticker,
    company_name="삼성전자",
    current_price=get_current_price(ticker),
    ...
)
result = run_debate(ctx)
print(result.final_signal, result.final_confidence, result.exit_reason)
```

---

## 6. 테스트 실행

```bash
# 전체 테스트
python -m pytest tests/ -v

# 커버리지 포함
python -m pytest tests/ -v --cov=. --cov-report=term

# 특정 모듈
python -m pytest tests/unit/test_agents.py -v
```

---

## 7. 코드 품질 검사

```bash
# 린트
ruff check .

# 포매팅
ruff format .

# 린트 + 포매팅 (커밋 전 실행)
ruff check . && ruff format .
```
