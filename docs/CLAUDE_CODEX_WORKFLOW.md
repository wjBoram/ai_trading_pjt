# Claude Code–Codex 협업 표준

## 목적

Claude Code와 Codex가 같은 작업 파일을 동시에 수정해 충돌하는 것을 막고, 한 에이전트의 구현을 다른
에이전트가 독립적으로 검증하도록 하는 개발 절차다. 이 문서는 개발 협업용이며, 런타임의 주식 신호
토론 프로토콜(`AI_AGENT_PROTOCOL.md`)과 구분한다.

## 규칙 파일 역할

| 범위 | 파일 | 용도 |
|---|---|---|
| Codex 전용 | `AGENTS.md` | Codex가 자동 적용하는 저장소 규칙 |
| Claude Code 전용 | `CLAUDE.md` | Claude Code가 자동 적용하는 프로젝트 컨텍스트 |
| 공통 | `docs/DEVELOPMENT_RULES.md` | 언어·구조·품질 기준 |
| 공통 | 이 문서 | 작업 분담, handoff, 교차 리뷰 |
| 공통 | `docs/PROJECT_REVIEW_2026-06-24.md` | 현재 기준 위험과 수정 순서 |

규칙이 충돌하면 사용자 지시가 우선한다. 도구별 파일에는 해당 도구의 실행 방식만 두고, 안전·품질
규칙은 공통 문서와 같은 방향을 유지한다.

## 기본 운영 모델

한 작업은 다음 두 역할로 나눈다.

1. 구현자: 요구사항 확인, 코드와 테스트 수정, 자체 검증, handoff 작성
2. 리뷰어: read-only로 diff/파일/테스트를 독립 검토하고 우선순위별 finding 작성

Claude와 Codex 중 어느 쪽도 항상 구현자 또는 리뷰어로 고정하지 않는다. 작업 특성과 사용자의 지정에
따라 역할을 바꾼다. 다만 같은 파일을 두 에이전트가 동시에 수정하지 않는다.

## 표준 작업 흐름

### 1. 작업 계약

구현 전에 아래를 짧게 확정한다.

- 목표와 비목표
- 변경할 가능성이 있는 파일
- 보존해야 할 동작과 데이터
- 안전 불변조건과 완료 기준
- 실행할 테스트와 실행할 수 없는 테스트

실거래, 외부 메시지, 의존성 변경, DB migration, `.env` 변경은 묵시적으로 범위를 넓히지 않고 별도
승인을 받는다.

### 2. 단일 작성자 구현

- 구현자만 겹치는 소스 파일을 수정한다.
- 리뷰어는 구현 중 read-only 탐색을 할 수 있지만 패치를 적용하지 않는다.
- 큰 작업은 서로 독립적인 디렉터리/인터페이스 계약으로 나뉠 때만 병렬 작성한다.
- 공유 인터페이스를 먼저 합의하고, 한쪽의 미완성 상태를 추측해 다른 쪽에서 맞추지 않는다.

### 3. Handoff

구현자는 다음 형식으로 리뷰어에게 전달한다. 지속 기록이 필요하면 관련
`conversations/sessions/<date>_<n>.md`에 같은 내용을 남긴다.

```markdown
## Handoff
- Goal:
- Non-goals:
- Changed files:
- Behavior changed:
- Safety invariants:
- Tests run and results:
- Tests not run and reason:
- Known risks / open questions:
- Review focus:
```

“테스트 통과”만 쓰지 말고 실제 명령과 결과를 적는다. 환경 문제로 실행하지 못한 검증은 성공으로
간주하지 않는다.

### 4. 독립 리뷰

리뷰어는 다음 순서로 본다.

1. 요청과 요구사항을 충족하는가
2. paper/live 경계와 fail-closed 원칙을 지키는가
3. 중복 주문, 동시성, 멱등성, stale data 위험이 없는가
4. DB transaction과 외부 호출 실패가 일관되게 처리되는가
5. 테스트가 실제 실패 모드를 검증하는가
6. 문서의 구현 상태가 코드와 일치하는가

리뷰 출력 형식:

```markdown
## Findings
- [P0|P1|P2|P3] 제목 — `path/to/file.py::symbol`
  - Evidence/reproduction:
  - Impact:
  - Required direction:

## Verification gaps
- 실행하지 못했거나 데이터가 부족한 검증

## Decision
- approve | approve-with-follow-up | changes-required
```

스타일 취향은 finding으로 올리지 않는다. 재현 가능성, 안전성, 정확성, 유지보수성에 영향을 주는
항목만 기록한다.

### 5. 수정과 종료

- 원 구현자가 finding을 수정한다. 리뷰어가 직접 수정하려면 역할 전환을 명시한다.
- P0/P1은 해결하거나 사용자가 명시적으로 수용하기 전까지 완료 처리하지 않는다.
- 해결 여부는 새 설명이 아니라 diff와 회귀 테스트로 확인한다.
- 요구사항 상태와 changelog를 실제 검증 수준에 맞게 갱신한다.

## 로컬 명령 예시 (Windows PowerShell)

이 환경에서는 PowerShell execution policy가 npm의 `.ps1` shim 실행을 막을 수 있으므로
`claude.cmd`, `codex.cmd`를 명시하는 편이 안정적이다.

Git 저장소가 아직 아닌 현재 경로에서 Codex read-only 리뷰:

```powershell
codex.cmd exec --skip-git-repo-check -C D:\stock_pjt_ai -s read-only `
  "AGENTS.md와 docs/CLAUDE_CODEX_WORKFLOW.md를 따르고 요청 범위만 코드 리뷰하라. 코드는 수정하지 말라."
```

Git 초기화 후 미커밋 변경 리뷰:

```powershell
codex.cmd exec review --uncommitted
```

Claude Code read-only 성격의 검토:

```powershell
claude.cmd -p --permission-mode plan `
  "CLAUDE.md와 docs/CLAUDE_CODEX_WORKFLOW.md를 따르고 요청 범위만 리뷰하라. 코드는 수정하지 말라."
```

CLI 옵션은 설치 버전에 따라 바뀔 수 있으므로 자동화에 넣기 전에 `codex.cmd exec --help`와
`claude.cmd --help`로 확인한다. 특히 런타임 코드에서 Codex를 비대화형으로 호출할 때는 현재 CLI의
`codex exec` 인터페이스를 사용해야 한다.

## 권장 리뷰 분담

| 변경 유형 | 구현자가 집중할 부분 | 리뷰어가 독립 확인할 부분 |
|---|---|---|
| 데이터 수집 | 공급자 어댑터, 정규화, provenance | 시각/주기 의미, 결측·중복·stale 처리 |
| AI 프롬프트/파싱 | schema, context 구성 | prompt injection, 경계값, 재현 평가 |
| 거래/리스크 | 상태 전이, transaction, broker adapter | 멱등성, 주문 후 비중, kill switch, fail closed |
| 스케줄러/API | job lifecycle, 입력 검증 | 중복 실행, 인증, 거래시간, 장애 복구 |
| 대시보드 | DTO와 표시 | DB session 수명, 민감정보 노출, 오해 가능한 라벨 |

## 의사결정 기록

에이전트 의견이 다르면 다음 근거 순서로 결정한다.

1. 사용자가 승인한 요구사항과 안전 경계
2. 재현 가능한 테스트 또는 실제 공급자 계약
3. 코드의 명시적 불변조건
4. `docs/ARCHITECTURE.md`의 ADR
5. 비용·복잡도·운영성 비교

중요한 구조 결정은 “두 AI가 합의함”이 아니라 선택지, 근거, 결과를 ADR로 기록한다.

