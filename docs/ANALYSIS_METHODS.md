# 주식 분석/예측 방법론 조사 문서

> 이 문서는 **순수 조사 자료**입니다. 실제 작업 상태의 단일 진실원천은 항상
> `docs/REQUIREMENTS.md`이며, 이 문서는 그 근거(왜 이 요구사항이 추가됐는지)를 제공합니다.

## 1. 목적과 범위

이 프로젝트는 기술적 지표와 뉴스 헤드라인을 기반으로 Claude+Codex 듀얼 AI 토론을 통해
매수/매도를 결정한다. 이 문서는 AI가 더 풍부한 근거로 판단할 수 있도록, 국내외에서
실제로 쓰이는 주식 분석/예측 방법론을 조사하고, 각각이 이 프로젝트에 언제·어떻게
적용 가능한지 평가한다.

## 2. 현재 구현 현황 요약

| 항목 | 위치 | 상태 |
|------|------|------|
| 기술지표 16종(RSI/MACD/BB/EMA/ATR/Stochastic/수익률/52주위치) | `indicators/technical.py` | 구현됨 |
| 퀀트 팩터(모멘텀 60일/이격도 EMA20) | `indicators/technical.py` | **이번 작업으로 추가** |
| 뉴스 헤드라인 수집 | `data/naver_scraper.py` | 구현됨 |
| 뉴스 감성 점수화(사전 기반) | `data/sentiment.py` | **이번 작업으로 추가** |
| 펀더멘털(재무제표) 분석 | - | 미구현 |
| 수급(외국인/기관 매매) 분석 | - | 미구현 |
| ML/DL 가격예측 | - | 미구현 (백로그 F-06) |
| 백테스트 | - | 미구현 (백로그 F-03) |

## 3. 방법론 카탈로그

### 3.1 기술적 분석 — 모멘텀 / 평균회귀 / 페어트레이딩

이미 RSI·MACD·볼린저밴드·EMA·ATR·Stochastic 16종이 구현되어 있다. 웹 리서치에 따르면
모멘텀은 중기(3~12개월) 구간에서, 평균회귀는 초단기(인트라데이)와 장기(3~5년) 구간에서
우세한 경향이 있어 두 팩터를 함께 쓰는 것이 일반적이다. 페어트레이딩은 평균회귀를
다종목으로 확장한 형태다. 이번 작업에서 `return_60d`(중기 모멘텀)와 `disparity_ema20`
(이격도, 평균회귀/과매수과매도 보조지표)을 추가했다.

### 3.2 뉴스/텍스트 감성분석 — 사전기반 vs FinBERT vs LLM 기반

- **사전/규칙 기반**: 키워드 빈도로 점수화. 외부 의존성 없음, 설명 가능, 정밀도는 낮음.
  이번 작업에서 `data/sentiment.py`로 구현(즉시 적용).
- **FinBERT**: 금융 텍스트에 특화된 BERT 모델. 사전기반보다 정확하지만 모델 다운로드/추론
  인프라가 필요(`requirements.txt` 변경 = 사용자 승인 필요).
- **LLM 기반(LLaMA-2 등)**: 최근 연구에서 FinBERT보다 높은 수익률을 보인다는 결과도 있음.
  이 프로젝트는 이미 Claude/Codex가 뉴스 헤드라인을 직접 읽으므로, 사실상 LLM 기반 감성
  해석을 토론 과정에서 암묵적으로 수행 중이라고 볼 수 있다.
- **하이브리드(ARIMAX+RandomForest+XGBoost)**: 감성과 수익률의 선형/비선형 관계를 함께
  포착. 이 프로젝트의 단순 평균 집계보다 정교하지만 별도 모델 학습 파이프라인 필요.

### 3.3 펀더멘털 분석 — DART/OpenDartReader, PER/PBR/ROE, DCF

DART OpenAPI(opendart.fss.or.kr)는 상장사 재무제표 전체 계정과목을 분기별로 무료
제공하며, `OpenDartReader` 파이썬 라이브러리로 쉽게 접근 가능하다. PER/PBR/ROE/DCF 중
복수 지표를 평균하는 것이 단일 지표보다 신뢰도가 높다는 연구 결과가 있다(특히 PBR은
ROE와 결합해서 봐야 의미가 있음 — 은행/보험 업종 등). 국내 KOSPI/KOSDAQ 종목 분석에
바로 적용 가능하나, 신규 데이터소스+DB 테이블이 필요해 중기 과제로 분류한다.

### 3.4 수급/시장 미시구조 — 외국인·기관 매매동향

`pykrx`는 OHLCV 외에 투자자별(개인/외국인/기관) 매매동향 데이터도 제공하는 것으로
알려져 있다. 현재 프로젝트는 이를 활용하지 않는다. 수급은 한국 시장에서 단기 가격
움직임의 선행 지표로 자주 참고되는 데이터로, 기존 `pykrx_client.py`를 확장하면 비교적
적은 변경으로 추가할 수 있다(중기 과제).

### 3.5 ML/DL 가격예측 — LSTM/Transformer 하이브리드, LightGBM

2025-2026 연구에서는 LSTM+Transformer 하이브리드(시계열 패턴 + 장거리 의존성)가
SOTA로 부상하고 있으며, 기술지표와 FinBERT 감성을 함께 입력하는 경향이 있다. 이
프로젝트의 백로그(`F-06`)에는 이미 LightGBM 기반 시그널 레이어가 등록되어 있다 — 이는
LSTM/Transformer보다 가볍고 설명 가능성이 높아 이 프로젝트의 "AI 토론에 참고자료 제공"
용도에 더 적합할 수 있다. 둘 다 별도 학습 파이프라인, 모델 버저닝, 재학습 주기 관리가
필요해 장기 과제로 분류한다.

### 3.6 멀티에이전트 LLM 트레이딩 프레임워크 — TradingAgents, FinRobot

TradingAgents(TauricResearch, LangGraph 기반)는 펀더멘털/감정/뉴스/기술 4개 분석가가
독립 분석 후, 강세/약세 연구자가 구조화된 토론을 거쳐, 거래팀→위험관리팀→포트폴리오
매니저가 최종 승인하는 구조다. 이 프로젝트의 Claude+Codex 2-agent 구조보다 역할이
세분화되어 있다. 참고할 점은 있으나, `agents/orchestrator.py`의 `_check_consensus()`
합의 로직 자체를 재설계해야 하는 큰 변경이므로, 먼저 1~2단계로 데이터(감성/펀더멘털/
수급)를 보강해 현재 2-agent 구조의 판단 품질을 높이는 것이 우선이라고 판단한다.

### 3.7 강화학습 기반 전략 — FinRL/FinRL-X

FinRL은 연구용(research-only) 강화학습 트레이딩 프레임워크로, 실거래 적용 시
sim-to-real 괴리에 주의해야 한다는 경고가 있다. 이 프로젝트는 `TRADING_MODE=paper`가
기본값이라는 안전장치가 이미 있으므로 격리된 실험은 가능하지만, 실거래(`live`) 전환과는
명확히 분리해야 한다.

### 3.8 백테스팅 프레임워크 — vectorbt / backtrader / backtesting.py

vectorbt는 NumPy/Numba 기반으로 대량 파라미터 탐색에 빠르고, backtrader는 고전적이지만
유지보수 우려가 있으며, backtesting.py는 단순 프로토타이핑에 적합하다. 이 프로젝트의
백로그(`F-03`, 6개월 백테스트)에 해당하며, 어떤 라이브러리든 `requirements.txt` 변경이
필요해 사용자 승인 대상이다.

## 4. 적용 가능성 매트릭스

| 방법론 | 적용시기 | 이유 | 현재 구현과의 연계점 | REQUIREMENTS ID |
|--------|---------|------|----------------------|-----------------|
| 뉴스 감성분석(사전기반) | 즉시 | 기존 `sentiment_score` 컬럼·`fetch_article_body` 인프라가 이미 절반 존재 | `data/data_manager.py`, `agents/protocol.py` | A-09 (완료) |
| 퀀트 팩터(모멘텀/이격도) | 즉시 | 신규 의존성·스키마 변경 없음 | `indicators/technical.py` | A-10 (완료) |
| 펀더멘털(DART) | 중기 | 신규 데이터소스+DB 테이블+Alembic 선행 필요 | `data/`, `core/models.py` | D-11/A-11 |
| 수급(외국인/기관) | 중기 | 신규 DB 테이블 필요, `pykrx` 확장으로 가능 | `data/pykrx_client.py` | D-12/A-12 |
| ML/DL 가격예측 | 장기 | 학습 파이프라인·모델 관리 필요 | 신규 모듈 | F-07 (F-06과 연계) |
| 멀티에이전트 세분화 | 장기 | 합의 로직 재설계 필요(영향 범위 큼) | `agents/orchestrator.py` | F-08 |
| RL 기반 전략 | 장기 | research-only, paper 모드 격리 필요 | 신규 모듈 | F-09 |
| 백테스트 프레임워크 | 장기 | 신규 의존성, 사용자 승인 필요 | 신규 `scripts/backtest.py` | F-03 (기존) |
| FinBERT/LLM 감성 | 보류 | 신규 의존성 필요, AI 토론이 이미 헤드라인을 직접 해석 중 | - | 채택 보류 |
| 소셜미디어(Reddit/StockTwits) 감성 | 보류 | 한국 개별 종목 관련 데이터 희소 | - | 채택 보류 |
| 옵션 변동성 | 보류 | 국내 개별주 옵션 시장 미성숙 | - | 채택 보류 |

## 5. 채택 보류 항목과 이유

- **FinBERT/LLM 기반 감성분석**: 별도 모델 추론 인프라(`requirements.txt` 변경)가
  필요하고, 이미 Claude/Codex가 뉴스 헤드라인을 직접 읽고 해석하므로 중복 효과가 제한적.
  사전기반 점수가 부족하다고 판단되면 재검토.
- **소셜미디어 감성(Reddit/StockTwits)**: 미국 시장 대비 한국 개별 종목에 대한 영어권
  소셜 데이터가 희소해 신뢰도가 낮을 것으로 판단.
- **옵션 변동성 지표**: 국내 개별 종목 옵션 시장이 미성숙해 데이터 가용성이 낮음.

## 6. 출처

- [TradingAgents (GitHub)](https://github.com/TauricResearch/TradingAgents)
- [TradingAgents: Multi-Agents LLM Financial Trading Framework (arXiv)](https://arxiv.org/html/2412.20138v5)
- [From Deep Learning to LLMs: A survey of AI in Quantitative Investment (arXiv)](https://arxiv.org/pdf/2503.21422)
- [Financial sentiment analysis using FinBERT (arXiv)](https://arxiv.org/abs/2306.02136)
- [Impact of LLMs news Sentiment Analysis on Stock Price Movement Prediction (arXiv)](https://arxiv.org/pdf/2602.00086)
- [Momentum Trading Guide — Quantt](https://www.quantt.co.uk/resources/momentum-trading-guide)
- [Mean Reversion Strategies — QuantInsti](https://blog.quantinsti.com/mean-reversion-strategies-introduction-building-blocks/)
- [전자공시 OPENDART 시스템](https://opendart.fss.or.kr/intro/main.do)
- [OpenDartReader 소개](https://wikidocs.net/230304)
- [Stock Valuation Methods: DCF, P/E, P/S 등](https://www.tradealgo.com/trading-guides/stocks/stock-valuation-methods-dcf-pe-ps-and-5-other-ways-to-value-a-company)
- [FinRL-X: An AI-Native Modular Infrastructure for Quantitative Trading (arXiv)](https://arxiv.org/html/2603.21330v1)
- [Python Backtesting Libraries Compared: VectorBT, Backtrader & More](https://pineify.app/resources/blog/best-python-backtesting-library-the-complete-guide-for-algorithmic-traders)
