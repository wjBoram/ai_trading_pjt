# 사용자 가이드

이 문서는 국내주식 AI 자동매매 시스템의 일상적인 사용 방법을 설명합니다.
설치·초기 설정은 [SETUP_GUIDE.md](SETUP_GUIDE.md)를 먼저 참조하세요.

---

## 1. 시스템 시작

### Windows (원클릭)

```bat
start.bat
```

- FastAPI 백엔드: `http://localhost:8000`
- Streamlit 대시보드: `http://localhost:8501`
- API 문서(Swagger): `http://localhost:8000/docs`

### 개별 실행

```bash
# 터미널 1: FastAPI 백엔드
python main.py

# 터미널 2: Streamlit 대시보드
streamlit run streamlit_app.py
```

---

## 2. 대시보드 페이지별 사용법

### 📊 Page 1 — 포트폴리오 현황 (`1_overview.py`)

| 항목 | 설명 |
|------|------|
| 총 자산 | 현금 + 보유 종목 평가액 |
| 가용 현금 | 즉시 투자 가능한 현금 |
| 오늘 손익 | 당일 실현·미실현 손익 합계 |
| 누적 손익 | 시스템 시작 이후 전체 손익 |
| 자산 추이 차트 | 최근 180일 총 자산 변화 |
| 보유 포지션 | 종목·수량·평균매입가·현재가·수익률 |

> 장중에는 30초마다 자동 갱신됩니다.

---

### 📈 Page 2 — 종목 분석 (`2_stock_analysis.py`)

1. 상단 종목 선택 드롭다운에서 종목 선택
2. 슬라이더로 조회 기간 선택 (20~180일)
3. 지표 요약: 현재가·RSI·MACD·거래량비율·52주 위치
4. Plotly 인터랙티브 캔들차트 확인
5. AI 최근 분석 신호·신뢰도·가중 점수 확인
6. 최근 뉴스 헤드라인 (최대 8개)

**사이드바 — 수기 갱신:**
- 데이터 유형 선택: OHLCV 일봉 / 최신 뉴스 / 분봉·시간봉
- 갱신 후 즉시 AI 분석 실행 토글
- **지금 갱신** 버튼 클릭

---

### 🤖 Page 3 — AI 토론 뷰어 (`3_ai_debate.py`)

AI 토론 세션의 전체 진행 과정을 라운드별로 확인합니다.

| 항목 | 설명 |
|------|------|
| 세션 선택 | 종목·날짜로 과거 토론 세션 선택 |
| 라운드 타임라인 | 라운드별 에이전트·신호·신뢰도·근거 |
| 수렴 시각화 | 신호 변화 흐름 차트 |
| 최종 결론 | 합의 신호·가중 점수·종료 사유 |
| 거래 실행 여부 | 리스크 관리 승인 결과 |

**종료 사유 코드:**

| 코드 | 의미 |
|------|------|
| `CONSENSUS` | 두 AI가 동일 신호로 합의 |
| `MAX_ROUNDS` | 최대 5라운드 도달, 가중 평균으로 결론 |
| `OSCILLATION` | BUY↔SELL 교대 교착 → HOLD 강제 |
| `LOW_CONFIDENCE` | 신뢰도 < 40% → HOLD 강제 |
| `TIMEOUT` | CLI 120초 초과 → HOLD 강제 |
| `CLI_ERROR` | CLI 실행 오류 → HOLD 강제 |

---

### 📋 Page 4 — 매매 이력 (`4_trade_log.py`)

- 전체 매매 이력 테이블 (종목·방향·수량·가격·손익·모드)
- 종목별 필터링
- **CSV 내보내기** 버튼 → 엑셀 분석 가능

---

### ⚙️ Page 5 — 설정 (`5_settings.py`)

| 항목 | 기본값 | 설명 |
|------|--------|------|
| 거래 모드 | `paper` | `live`로 변경 시 실제 주문 실행 |
| AI 신뢰도 임계값 | 65% | 미만 시 거래 미실행 |
| 최대 포지션 비중 | 20% | 종목당 포트폴리오 비중 상한 |
| 손절선 | -5% | 평균매입가 대비 손실률 |
| 일일 손실 한도 | -3% | 초과 시 신규 매수 중단 |
| 최대 동시 보유 | 5개 | 동시 보유 종목 수 상한 |

> ⚠️ 설정 변경은 `.env` 파일 편집 후 시스템 재시작이 필요합니다.

---

## 3. 데이터 갱신 방법

### 3-1. 배치 자동 갱신 (스케줄러)

시스템이 실행 중이면 자동으로 처리됩니다:

| 시각 (KST) | 작업 |
|-----------|------|
| 08:50 | 전일 OHLCV 수집 + 기술 지표 계산 |
| 09:10 | AI 토론 실행 + 매매 신호 생성 |
| 09:00~15:30 매 5분 | 분봉·시간봉 갱신 |
| 15:40 | 당일 OHLCV 확정 저장 + 포트폴리오 스냅샷 |
| 16:00 | NAVER 뉴스 수집 + AI 재분석 트리거 |

### 3-2. 대시보드 수기 갱신

대시보드 사이드바 → **데이터 갱신** 패널:

1. 갱신할 데이터 유형 체크 (OHLCV / 뉴스 / 분봉)
2. 분봉 갱신 시 간격 선택 (1m / 5m / 10m / 30m / 60m)
3. **갱신 후 즉시 AI 분석** 토글 켜기
4. **지금 갱신** 클릭

### 3-3. REST API 수기 갱신

```bash
# 비동기 갱신 (즉시 반환, 백그라운드 처리)
curl -X POST http://localhost:8000/api/refresh/manual \
  -H "Content-Type: application/json" \
  -d '{"tickers":["005930","000660"],"data_types":["ohlcv","news"],"trigger_analysis":true}'

# 동기 갱신 (완료 후 결과 반환)
curl -X POST http://localhost:8000/api/refresh/manual/sync \
  -H "Content-Type: application/json" \
  -d '{"tickers":["005930"],"data_types":["ohlcv"],"trigger_analysis":true}'

# 분봉 갱신
curl -X POST http://localhost:8000/api/refresh/intraday \
  -H "Content-Type: application/json" \
  -d '{"interval":"5m","trigger_analysis":false}'

# 최신 가격 캐시 조회
curl http://localhost:8000/api/refresh/prices

# 마지막 갱신 시각
curl http://localhost:8000/api/refresh/status
```

### 3-4. 가격 변화 자동 AI 재분석

시스템이 실행 중이면 0.5% 이상 가격 변화 발생 시 자동으로 AI 재분석이 트리거됩니다.
(5분 인터벌 배치 갱신 시 내부적으로 감지)

---

## 4. AI 분석 수동 실행

### 대시보드에서

`3_ai_debate.py` 페이지 → 종목 선택 → **AI 분석 시작** 버튼

### Python 직접 실행

```python
from agents.orchestrator import run_debate, save_session_to_db
from agents.protocol import MarketContext
from data.data_manager import get_market_context

# 시장 컨텍스트 생성
ctx = get_market_context("005930")  # 삼성전자

# AI 토론 실행 (최대 5라운드)
result = run_debate(ctx)

print(f"신호: {result.final_signal}")
print(f"신뢰도: {result.final_confidence:.0%}")
print(f"가중 점수: {result.weighted_score:+.3f}")
print(f"종료 사유: {result.exit_reason}")
print(f"거래 실행: {result.execute_trade}")

# DB 저장
save_session_to_db("005930", result)
```

---

## 5. 모의거래 vs 실거래 전환

> ⚠️ **실거래 전환은 매우 신중하게 결정하세요. 실제 자금이 투입됩니다.**

### 모의거래 (기본)

`.env` 파일:
```env
TRADING_MODE=paper
```

### 실거래 전환 절차

1. KIS OpenAPI 신청 및 승인 완료 확인
2. `.env` 파일 업데이트:
   ```env
   TRADING_MODE=live
   KIS_APP_KEY=your_app_key
   KIS_APP_SECRET=your_app_secret
   KIS_ACCOUNT_NUMBER=your_account_number
   KIS_BASE_URL=https://openapi.koreainvestment.com:9443
   ```
3. 시스템 재시작
4. `5_settings.py` 페이지에서 `🔴 실거래` 모드 배지 확인

**샌드박스 테스트 (권장):**
```env
TRADING_MODE=live
KIS_BASE_URL=https://openapivts.koreainvestment.com:9443  # 테스트 서버
```

---

## 6. 개발 관련 작업

### 코드 품질 검사

```bash
ruff check .          # 린트
ruff format .         # 포매팅
```

### 테스트 실행

```bash
python -m pytest tests/ -v             # 전체
python -m pytest tests/unit/ -v        # 단위 테스트만
python -m pytest tests/ -v --cov=.     # 커버리지 포함
```

### DB 재초기화

```bash
python scripts/setup_db.py        # 테이블 생성 + 종목 마스터
python scripts/backfill_data.py   # 2년치 OHLCV 백필
```

---

## 7. AI 세션 이어서 작업하기

새 Claude Code 세션을 시작할 때 컨텍스트를 빠르게 복원하려면:

```
CLAUDE.md와 conversations/SESSIONS.md를 읽고,
마지막 세션(conversations/sessions/최신파일.md)도 참조해서
이전 작업에서 이어서 개발해줘.
```

### 대화 세션 저장

현재 대화를 저장하려면 Claude Code에게 직접 요청:
```
이번 대화 내용을 conversations/sessions/ 에 저장해줘.
```

또는 스크립트로 빈 세션 파일 생성:
```bash
python scripts/save_context.py --summary "작업 내용 요약"
```

---

## 8. 주요 API 엔드포인트 요약

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 시스템 상태·거래 모드 확인 |
| GET | `/api/portfolio` | 포트폴리오 현황 |
| GET | `/api/stocks` | 추적 종목 목록 |
| GET | `/api/stocks/{ticker}/ohlcv` | 종목 OHLCV 데이터 |
| GET | `/api/sessions` | AI 토론 세션 목록 |
| GET | `/api/trades` | 매매 이력 |
| POST | `/api/refresh/manual` | 수기 갱신 (비동기) |
| POST | `/api/refresh/manual/sync` | 수기 갱신 (동기) |
| POST | `/api/refresh/intraday` | 분봉·시간봉 갱신 |
| GET | `/api/refresh/prices` | 최신 가격 캐시 |
| GET | `/api/refresh/status` | 마지막 갱신 시각 |

전체 API 문서: `http://localhost:8000/docs`

---

## 9. 문제 해결

### "데이터 없음" 오류

```bash
# DB 초기화 후 백필
python scripts/setup_db.py
python scripts/backfill_data.py
```

### AI CLI 사용 불가

```bash
# 설치 확인
claude --version
codex --version

# 재설치
npm install -g @anthropic-ai/claude-code
npm install -g @openai/codex
```

CLI 미설치 시 시스템은 자동으로 SDK 폴백 모드로 전환됩니다 (`.env`에 API 키 필요).

### 포트 충돌

```bash
# 사용 중인 포트 확인 (Windows)
netstat -ano | findstr :8000
netstat -ano | findstr :8501
```

`.env`에서 포트 변경:
```env
API_PORT=8001
DASHBOARD_PORT=8502
```

### 로그 확인

```bash
# 최근 로그
tail -f logs/app.log      # 시스템 로그
tail -f logs/trades.log   # 거래 이벤트 로그
```
