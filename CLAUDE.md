# D:\stock_pjt_ai — 멀티 프로젝트 레포

이 레포는 단일 프로젝트가 아니라 **워크스페이스 2개 + 공유 인프라 2개**로 구성된다.

## 하위 프로젝트

- [`claude_codex_workspace/`](claude_codex_workspace/CLAUDE.md) — 사용자·Claude·Codex가 하나의 영속적인 채팅방(Room)에서 함께 대화하며, AI 둘이 토론·리뷰하다가 사용자 판단이 필요하면 호출하는 자동화 도구. (Phase 1, 코드 미구현 — 골격+표준 룰만 존재)
- [`stock_workspace/`](stock_workspace/CLAUDE.md) — AI 기반 주식 분석 프로젝트. (경량 골격만, 상세 설계는 다음 단계)

각 워크스페이스의 `CLAUDE.md`가 더 구체적인 범위에서 이 문서보다 우선한다.

## 공유 디렉토리

- [`chat_rooms/`](chat_rooms/README.md) — 방(room) 단위 대화 아카이브. 어느 워크스페이스에서 작업하든 공용으로 쓴다.
- [`runtime_logs/`](runtime_logs/README.md) — AI 호출/상태/실시간 로그. 마찬가지로 공용.

## 문서 읽기 순서

1. `docs/STANDARD_RULES.md` — 표준 룰 본문 (디렉토리 맵, Room/Task 모델, 실행 방식, AI 운영 모델)
2. `docs/JSON_SCHEMAS.md` — 방/메시지/task/세션/로그 JSON 스키마
3. `docs/GLOSSARY.md` — 용어집
4. `docs/DESIGN_GAPS.md` — 알려진 한계와 다음 단계

## AI 협업 메타 규칙 (요약, 상세는 STANDARD_RULES.md)

- AI는 서로의 제안을 승인·완료로 마킹할 권한이 없다 — **자동 승인 금지**.
- 모든 task는 사용자의 최종 판단으로만 `COMPLETED`/`CANCELLED`된다.
- AI가 결론에 도달하거나 판단이 필요하면 task를 `WAITING_USER_DECISION`으로 전이하고 사용자를 부른다.
- 한 AI를 호출하는 동안 다른 AI를 동시에 호출하지 않으며, AI가 서로의 응답을 스스로 polling하지 않는다(Async Guardrail).

## 현재 구현 상태

디렉토리 골격과 표준 룰 문서만 존재한다. watcher/오케스트레이터/웹 UI 등 실제 코드는 아직 구현되지 않았다(Phase 1 다음 단계).
