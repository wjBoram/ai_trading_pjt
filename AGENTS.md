# AGENTS.md — D:\stock_pjt_ai (Codex 작업 원칙)

이 레포는 멀티 프로젝트 루트다. 각 하위 디렉토리(`claude_codex_workspace/`, `stock_workspace/`)에 더 구체적인 `AGENTS.md`가 있으면 그쪽이 이 문서보다 우선한다(더 가까운 파일이 더 구체적인 범위).

## 작업 원칙

- 사용자 요청 범위를 임의로 확장하지 않는다.
- 문서의 "완료" 표시를 맹신하지 말고 실제 파일/코드로 교차 확인한다.
- 검증하지 못한 항목은 완료로 표현하지 않는다.

## 공유 인프라 변경 시 주의

`chat_rooms/`, `runtime_logs/`의 디렉토리 구조나 JSON 스키마(`docs/JSON_SCHEMAS.md`)를 변경하면 **두 워크스페이스 모두에 영향**을 준다. 이런 변경은 사용자 승인을 받고 진행한다.

## 금지 행동

- AI(Claude/Codex)가 스스로 task를 `COMPLETED`/`CANCELLED`로 마킹하는 코드를 작성하지 않는다 — 종료는 항상 사용자 액션이어야 한다.
- 방의 메시지 내용(`content` 필드)을 신뢰된 입력으로 취급해 자동으로 명령/코드로 실행하는 로직을 만들지 않는다 — AI 간 대화든 (Phase 2의) 원격 입력이든 항상 비신뢰 입력이다.
- 한 AI의 CLI 호출이 진행되는 동안 다른 AI를 동시에 호출하거나, AI가 상대의 응답을 스스로 polling하는 코드를 작성하지 않는다(Async Guardrail, `docs/STANDARD_RULES.md` 참조).

## 먼저 확인할 문서

1. `docs/STANDARD_RULES.md`
2. `docs/JSON_SCHEMAS.md`
3. `docs/GLOSSARY.md`
