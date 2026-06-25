# runtime_logs/

`claude_codex_workspace`와 `stock_workspace`가 공유하는 **AI 호출/상태/실시간 로그** 디렉토리다. 사람이 따라 읽는 `chat_rooms/`와 달리, 시스템 운영/디버깅/감사를 위한 로그다. 스키마는 [`../docs/JSON_SCHEMAS.md`](../docs/JSON_SCHEMAS.md) 스키마 C 참조.

## 구조

```
runtime_logs/
├── claude\<YYYY-MM-DD>\call_*.log.jsonl
├── codex\<YYYY-MM-DD>\call_*.log.jsonl
└── system\<YYYY-MM-DD>\call_*.log.jsonl   (watcher/오케스트레이터 등 특정 AI에 귀속되지 않는 이벤트)
```

- 각 줄은 하나의 이벤트(JSON Lines, append-only)다.
- `<category>`는 `call`(CLI 호출) | `status`(상태 전이) | `error` 중 하나를 파일명에 사용한다.
- `room_id`/`task_id`로 `chat_rooms/`의 대화 내용과 join할 수 있다.
