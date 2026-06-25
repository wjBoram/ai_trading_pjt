# chat_rooms/

`claude_codex_workspace`와 `stock_workspace`가 공유하는 **방(room) 단위 대화 아카이브**다. 상세 스키마는 [`../docs/JSON_SCHEMAS.md`](../docs/JSON_SCHEMAS.md), 개념 설명은 [`../docs/STANDARD_RULES.md`](../docs/STANDARD_RULES.md) 1장 참조.

## 구조

```
chat_rooms/
└── <room_id>/
    ├── room_meta.json          방 메타데이터 + task 인덱스 + AI별 session_state (갱신형, atomic overwrite)
    └── <YYYY-MM-DD>/
        └── messages.jsonl      그 날짜의 메시지 로그 (append-only, JSON Lines)
```

- 방(`room_id`)은 영속적이다 — 날짜 폴더는 메시지 로그를 관리하기 위한 파티션일 뿐, 방 자체가 그날 끝나는 것은 아니다.
- `room_id` 명명 규칙: `room-<kebab-slug>` (예: `room-claude-codex-main`).
- **단일 작성자 원칙**: 방마다 그 방을 담당하는 오케스트레이터 1개만 이 디렉토리의 파일을 쓴다. Claude/Codex CLI는 직접 파일에 쓰지 않는다.

## 현재 방 목록

- `room-claude-codex-main` — Claude-Codex 토론방 (Phase 1 기본 방)
