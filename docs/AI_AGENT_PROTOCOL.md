# AI 듀얼 에이전트 프로토콜 상세 명세

## 개요

이 시스템은 두 개의 독립 AI(Claude, Codex)가 같은 시장 데이터를 보고 토론하여 매수/매도 결정을 내린다.
단순한 앙상블이 아닌 **상호 비판과 합의 프로세스**를 통해 단일 모델보다 강건한 결정을 목표로 한다.

---

## 로컬 CLI 실행 방식

```
로컬 PC
├── claude CLI  (npm install -g @anthropic-ai/claude-code)
└── codex CLI   (npm install -g @openai/codex)
         ↑
         └── agents/local_cli_runner.py
               subprocess.run(["claude", "--print", ...], input=prompt)
               subprocess.run(["codex", "--quiet"], input=prompt)
```

CLI가 없으면 SDK 폴백:
- `claude` 없음 → `anthropic` SDK + `claude-sonnet-4-6` 모델
- `codex` 없음 → `openai` SDK + `gpt-4o` 모델

---

## 라운드별 역할 정의

### Round 1 — Claude 초기 분석 (`agents/prompts/claude_initial.py`)

**입력**: MarketContext (OHLCV 20일, 기술 지표, 뉴스 5-10개)

**역할**: 퀀트 애널리스트로서 독립적 초기 분석

**출력 형식**:
```json
{
  "signal": "BUY" | "SELL" | "HOLD",
  "confidence": 0.0~1.0,
  "reasoning": "200자 이내 (지표 수치 인용 필수)",
  "key_factors": ["요인1", "요인2", "요인3"],
  "risk_level": "low" | "medium" | "high"
}
```

---

### Round 2 — Codex 검토 (`agents/prompts/codex_review.py`)

**입력**: MarketContext + Round 1 Claude 분석 전체

**역할**: 리스크 애널리스트로서 독립 평가 후 Claude 분석 비판적 검토

**추가 출력 필드**:
```json
{
  ...,
  "agreement_with_prior": true | false,
  "disagreement_points": ["반박1", "반박2"]
}
```

---

### Round 3~5 — 협상 (`agents/prompts/negotiation.py`)

**홀수 라운드**: Claude (Codex 비판에 대한 반론)
**짝수 라운드**: Codex (Claude 반론에 대한 재검토)

**전체 대화 히스토리** 프롬프트에 포함 → 각 AI가 토론 흐름 파악

**추가 출력 필드**:
```json
{
  ...,
  "signal_changed": true | false
}
```

---

## 수렴·중단 조건 상세

| 조건 | 코드 | 트리거 | 결과 | 거래 실행 |
|------|------|--------|------|---------|
| A | LOW_CONFIDENCE | 어느 AI든 confidence < 0.40 | HOLD 강제 | ✗ |
| B | CONSENSUS | 동일 신호 + avg_conf ≥ 0.65 | 해당 신호 | ✓ (리스크 승인 시) |
| C | LOW_CONFIDENCE | codex confidence < 0.40 | HOLD 강제 | ✗ |
| D | OSCILLATION | 최근 3라운드 BUY↔SELL 교대 | HOLD 강제 | ✗ |
| E | MAX_ROUNDS | round = MAX_ROUNDS (기본 5) | 가중 평균 | 신뢰도 충족 시만 |
| F | TIMEOUT | subprocess 120초 초과 | HOLD 강제 | ✗ |

---

## 가중 합의 점수 계산

```
BUY=+1, HOLD=0, SELL=-1

round_weights = exponential_decay(n_rounds)
# 예: 3라운드면 [0.21, 0.33, 0.46] (최신 라운드 가중치 높음)

weighted_score = Σ (weight_i × signal_score_i × confidence_i)

BUY  if weighted_score ≥ +0.35
SELL if weighted_score ≤ -0.35
HOLD otherwise
```

---

## 매수/매도 목표가 계산

```python
atr_pct = indicators["atr_pct"]  # ATR / 현재가 (변동성 기반)

BUY 신호:
  buy_price  = current_price × (1 - atr_pct × 0.5)   # 소폭 할인 진입
  sell_price = current_price × (1 + atr_pct × 2.0)   # 2 ATR 익절

SELL 신호 (보유 시 청산):
  sell_price = current_price × 1.002   # 소폭 프리미엄 지정가
  buy_price  = current_price × 0.95    # 5% 하락 시 재매수 참고가
```

---

## 프롬프트 설계 원칙

1. **구조화 출력 강제**: 모든 프롬프트는 JSON 코드 블록만 반환하도록 지시
2. **수치 인용 필수**: 추상적 표현 금지, 실제 RSI 값·MACD 값 등 인용 요구
3. **역할 분리 명확화**: Claude=퀀트 분석, Codex=리스크 검토로 역할 구분
4. **히스토리 전달**: 협상 라운드는 이전 전체 대화 포함 (문맥 유지, 한 토론 세션 내부 한정 —
   세션 간 연속성은 별도 절 "세션 간 연속성 정책" 참조)
5. **응답 길이 제한**: reasoning 200자 이내 (비용·처리 속도 최적화)

---

## DB 저장 구조

토론 세션 1회 = `agent_sessions` 레코드 1건 + `agent_rounds` 레코드 N건

```
agent_sessions
  id=1, ticker="005930", session_date=2026-06-23
  total_rounds=2, final_signal="BUY", final_confidence=0.725
  weighted_score=0.52, exit_reason="CONSENSUS", execute_trade=True
  buy_price=71640, sell_price=74160

agent_rounds (session_id=1)
  round=1, agent="claude", signal="BUY", confidence=0.75, reasoning="..."
  round=2, agent="codex",  signal="BUY", confidence=0.70, agreement=True
```

Streamlit Page 3 (`dashboard/pages/3_ai_debate.py`)에서 이 데이터를 라운드별 카드로 시각화.

---

## 세션 간 연속성 정책 (Cross-Session Continuity Rule)

위 "히스토리 전달"(프롬프트 설계 원칙 4번)은 **한 번의 `run_debate()` 호출 내부**(Round
1~5)에서만 적용된다. 이 절은 그와 별도로, **`run_debate()`가 다시 호출될 때마다**(다음 날
스케줄, 뉴스 갱신 트리거, 가격 0.5% 변동 트리거, 대시보드 수동 실행 등 — 즉 모든 트리거
경로 공통) 동일 종목의 과거 분석을 어떻게 다음 토론에 반영하는지를 규정하는 **rule**이다.

### 규칙

1. **항상 자동 적용**: `MarketContext`를 생성하는 모든 지점(`scheduler/tasks.py::run_analysis_for_ticker()`,
   `dashboard/pages/3_ai_debate.py` 수동 실행)은 토론을 시작하기 전에 반드시
   `agents/orchestrator.py::get_recent_sessions(ticker)`를 호출해 `MarketContext.prior_sessions`
   를 채운다. 별도 설정이나 수동 개입 없이 매 실행마다 자동으로 작동한다.
2. **조회 범위**: 동일 종목(ticker)의 과거 세션만 조회한다(다른 종목 간 교차 참조는 하지
   않음). 개수는 `config/settings.py::prior_sessions_limit`(기본 3개)이며, `agent_sessions.id`
   내림차순(최신순)으로 정렬한다 — `created_at`은 초 단위 해상도라 같은 초에 여러 세션이
   생성되면 순서가 불안정해질 수 있어 자동증가 PK를 기준으로 정렬한다.
3. **포함 정보**: 세션별로 `session_date`, `final_signal`, `final_confidence`, `exit_reason`,
   그리고 해당 세션의 마지막 라운드 `reasoning`(150자 truncate)을 `PriorSessionSummary`
   (`agents/protocol.py`)로 묶어서 전달한다.
4. **적용 범위**: `agents/prompts/context_builder.py::build_market_context_text()`가
   `[과거 분석 이력]` 섹션으로 렌더링하며, Round 1(`claude_initial.py`)·Round 2
   (`codex_review.py`)·Round 3+(`negotiation.py`) **세 프롬프트 빌더 모두가 공통으로
   이 함수를 호출**하므로 별도 수정 없이 모든 라운드가 동일하게 과거 이력을 본다.
5. **첫 분석 처리**: 해당 종목의 과거 세션이 없으면 `get_recent_sessions()`는 빈 리스트를
   반환하고, 프롬프트에는 "(과거 분석 이력 없음 - 첫 분석)"으로 명시된다. 에러로 취급하지
   않는다.
6. **라운드가 0건인 세션**(CLI 오류 등으로 한 라운드도 완료되지 못한 경우)도 이력에는
   포함되며, `last_reasoning`은 빈 문자열로 표시된다 — AI가 "지난 시도가 실패했었다"는
   사실 자체를 참고할 수 있게 한다.

### 의도적 설계 — CLI 자체 세션 기능을 쓰지 않는 이유

`agents/local_cli_runner.py`는 `claude`/`codex` CLI를 매 라운드마다 완전히 새로운 독립
subprocess로 실행하며 `--resume`/`--session-id` 같은 CLI 자체 세션 플래그를 쓰지 않는다.
세션 간 연속성도 이와 동일하게 **DB에 저장된 과거 결과를 텍스트로 재구성해 프롬프트에
포함**시키는 방식으로 구현한다 — 이미 라운드 간 히스토리 전달에 쓰이는 방식과 동일한
패턴이므로, 새로운 메커니즘(CLI 세션 지속, 별도 캐시 등)을 추가로 도입하지 않는다.
