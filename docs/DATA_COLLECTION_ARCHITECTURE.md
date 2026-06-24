# 데이터 수집 및 아키텍처 가이드라인

> 이 문서는 **현재 10개 종목**(005930 삼성전자, 000660 SK하이닉스, 373220 LG에너지솔루션,
> 207940 삼성바이오로직스, 005380 현대차, 000270 기아, 068270 셀트리온, 105560 KB금융,
> 055550 신한지주, 028260 삼성물산)에 적용된 데이터 수집/아키텍처 조사 자료다. 작업 상태의
> 단일 진실원천은 항상 `docs/REQUIREMENTS.md`이며, 코드 리스크 평가는
> `docs/PROJECT_REVIEW_2026-06-24.md`를 따른다.

## DB 휘발성에 대한 정정

`core/database.py`는 `data_store/trading.db`(SQLite **파일**)를 사용하므로 이미 영속적이며
프로젝트 종료로 휘발되지 않는다. 휘발되는 건 `data/realtime_collector.py`의 인메모리 가격
캐시뿐이고, 이는 재실행 시 자동 재생성되는 저위험 데이터다. 이 문서의 "파일 아카이브"는
DB 휘발 문제를 해결하기 위한 것이 아니라 **백업·휴대성·재현성** 목적으로 추가한다.

## 1. 수집 데이터 정의

| 카테고리 | 상태 | 주기 제안 | 비고 |
|---|---|---|---|
| 일봉 OHLCV | ✅ 완료 | 일 1회(08:50) | `data/pykrx_client.py::fetch_ohlcv()` |
| 월봉/연봉 OHLCV | ✅ 이번에 구현 | 필요 시 수동 | `fetch_ohlcv_monthly()`/`fetch_ohlcv_yearly()`, pykrx `freq='m'/'y'` |
| 주봉 OHLCV | ✅ 이번에 구현 | 필요 시 수동 | `fetch_ohlcv_weekly()`, pykrx가 주봉 freq를 지원하지 않아 일봉을 `pandas.resample('W-FRI')`로 파생 |
| 분봉/실시간 시세 | ❌ pykrx 자체가 미지원, 기존 구현도 버그 상태 | - | `docs/PROJECT_REVIEW_2026-06-24.md` P0-3 참조 — `get_current_price()`는 당일 종가일 뿐 실시간이 아니고, intraday 저장 테이블도 없음. 사용자 결정으로 이번 범위에서 제외 |
| 뉴스 헤드라인·본문·감성 | ✅ 완료(A-09) | 1일 1회 + 즉시갱신 | |
| 재무제표 | ❌ 미구현(백로그 D-11/A-11) | 분기 1회 | DART OpenAPI, 이번 범위 아님 |
| 수급(외국인/기관) | ❌ 미구현(백로그 D-12/A-12) | 일 1회 | pykrx `get_market_trading_value_by_investor` 확인됨, 이번 범위 아님 |
| **(신규) 매크로 지표** | ❌ 백로그 등록만(D-15) | 일/주 1회 | 환율(USD/KRW), 기준금리 — 수출 비중 큰 종목 다수라 영향 큼. 한국은행 ECOS API |
| **(신규) 시장 지수** | ❌ 백로그 등록만(D-15) | 일 1회 | KOSPI/KOSDAQ 지수, pykrx `get_index_ohlcv` 이미 존재 |
| **휴장일 캘린더** | ✅ 이번에 구현(D-13) | 연 1회 수동 갱신 | 기존 버그: 평일에도 한국 공휴일을 모르고 분석/스케줄 작업을 시도함 |
| AI 토론 히스토리/매매 이력 | ✅ 완료 | - | 기존 DB. 단, `docs/PROJECT_REVIEW_2026-06-24.md` P0-1 — Codex CLI 라운드가 현재 잘못된 인자로 실패하는 별도 이슈 있음 |

## 2. 데이터 수집 경로·도구

| 데이터 | 소스 | 비용 | 상태 |
|---|---|---|---|
| 일/월/연봉, 시장지수, 수급 | `pykrx`(이미 설치됨) | 무료 | 신규 의존성 없음 |
| 주봉 | 일봉 → `pandas.resample('W-FRI')` 파생 | 무료 | 신규 의존성 없음 |
| 분봉/실시간 | KIS OpenAPI WebSocket | 무료(계좌 필요) | Phase 3 대상 |
| 재무제표 | DART OpenAPI + `OpenDartReader` | 무료(API키) | 백로그 D-11 |
| 환율/기준금리 | 한국은행 ECOS OpenAPI | 무료(API키) | 백로그 D-15 |
| 휴장일 | `config/market_calendar.py`의 정적 연간 리스트 | 무료 | 이번에 구현. `holidays` 같은 신규 패키지 추가는 회피(requirements.txt 변경=승인 필요) |

## 3. 아키텍처/파이프라인 (기존 구조 확장)

기존 `config→core→data→indicators→agents→trading→scheduler→api→dashboard` 단방향 의존성을
그대로 따른다(`AGENTS.md`/`CLAUDE.md` 공통 규칙).

```
스케줄러(08:50/09:10/5분간격/15:40/16:00, 평일 + 휴장일 제외)
  → data/(OHLCV·뉴스 수집) → indicators/(지표 계산)
  → agents/(Claude+Codex 토론, MarketContext 4개 연결지점)
  → trading/order_executor → risk_manager → paper_broker(DB 기록)
  → dashboard/(5페이지)
```

> ⚠️ `agents/`→`trading/` 경로와 리스크 검증에는 `docs/PROJECT_REVIEW_2026-06-24.md`의
> P0-2(분석/주문 미분리), P1-1(현금 이중차감), P1-4(누적 비중 미검증) 등 알려진 결함이 있다.
> 이 문서가 다루는 범위는 데이터 수집 계층이며, 거래 실행 계층 결함은 별도로 추적한다.

**저장 방식 (2계층, 백업/재현성 목적)**:
1. **1차(이미 영속적)**: SQLite `data_store/trading.db` — 단일 진실 원천.
2. **2차(신규, 백업/휴대용)**: `data_store/price_archive/{ticker}/{timeframe}.json` —
   `scripts/collect_price_archive.py --ticker <코드|all> --timeframe <daily|weekly|monthly|yearly> [--days N]`로
   종목+시간단위 하나씩 수집. 일봉은 기존 `data_manager.upsert_ohlcv()`로 DB도 함께 갱신.
   인덱스는 `data_store/price_archive/ARCHIVE_INDEX.md`(`conversations/SESSIONS.md`와 동일한
   "MD 인덱스 + 구조화 파일" 패턴 재사용).
   **재적재**: `scripts/load_price_archive.py --ticker <코드|all>`가 JSON을 읽어 `OHLCVDaily`를
   복원(일봉만 — 주/월/연봉은 전용 DB 테이블이 없어 파일 보관까지만, 테이블 추가 시 확장).
   - 구현 시 발견한 함정: `pandas.read_json()`이 `dtype` 지정 없이는 "005930" 같은 종목코드를
     숫자로 잘못 추론해 앞자리 0을 잃는다 — `dtype={"ticker": str}` 필수.

## 4. 개발 로드맵 (기존 Phase 번호 체계 + Codex 리뷰 반영)

| Phase | 내용 | 상태 |
|---|---|---|
| 1-2 | 데이터수집·AI에이전트·모의거래·대시보드 | ✅ 완료(단, 세부 결함은 PROJECT_REVIEW 참조) |
| 2.5(이번 작업) | 월/주/연봉 수집 + JSON 아카이브/재적재 + 휴장일 인식 | ✅ 완료 |
| **Gate 0(권장 최우선)** | Codex CLI 인자 수정(P0-1), 분석/주문 분리(P0-2), live 진입 차단(P0-4) | ⏳ 미착수 — `docs/PROJECT_REVIEW_2026-06-24.md` 참조 |
| 3 | KIS OpenAPI 실거래+분봉/실시간 시세 | ⏳ 예정 |
| 4 | DART 펀더멘털(D-11), 수급(D-12), 매크로/지수(D-15), KOSDAQ 확장 | 백로그 |
| 5 | ML 시그널(F-06/F-07), 백테스트(F-03), 멀티에이전트 세분화(F-08) | 백로그 |

## 출처

- [전자공시 OPENDART 시스템](https://opendart.fss.or.kr/intro/main.do)
- [한국은행 ECOS OpenAPI](https://ecos.bok.or.kr/)
- [2026년 한국 공휴일 — publicholidays.co.kr](https://publicholidays.co.kr/ko/2026-dates/)
- [2026년 공휴일 — superkts.com](https://superkts.com/day/holiday/2026)
