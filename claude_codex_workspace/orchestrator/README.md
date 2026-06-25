# orchestrator/

다음 발화자 판정, task 상태 전이, AI 세션 간 메시지 push 로직이 들어갈 자리([`../../docs/STANDARD_RULES.md`](../../docs/STANDARD_RULES.md) 2.3, 5장 참조).

## 들어갈 것 (다음 단계)

- 방마다 단일 작성자로서 `messages.jsonl`/`room_meta.json`을 쓰는 로직(단일 작성자 원칙).
- 메시지를 상대 AI의 세션에만 push하는 단방향 컨텍스트 전달 로직.
- task 상태 머신: `OPEN → IN_PROGRESS ⇄ WAITING_USER_DECISION → COMPLETED|CANCELLED` (종료는 사용자만 트리거).
- Async Guardrail: 한 AI 호출이 끝날 때까지 다른 AI를 호출하지 않음.

## 이번 범위 아님

실제 구현 코드는 다음 단계에서 작성한다.
