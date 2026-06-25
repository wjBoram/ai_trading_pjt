# JSON 스키마

`schema_version` 필드는 모든 스키마에 의무화한다. 필드 추가는 호환 가능한 변경으로 취급하고, 필드 제거/타입 변경 시에만 버전을 올린다.

## 스키마 A — 방 메시지 로그

경로: `chat_rooms/<room_id>/<YYYY-MM-DD>/messages.jsonl` (JSON Lines, 한 줄 = 한 메시지)

```json
{
  "schema_version": "1.0",
  "room_id": "room-claude-codex-main",
  "message_id": "uuid4",
  "task_id": "tk-20260625-001 | null",
  "sender": "user | claude | codex | system",
  "timestamp": "ISO8601",
  "content": "string",
  "content_hash": "string (중복 트리거 감지용)",
  "conclusion_tag": "string | null",
  "needs_user_input": false,
  "in_reply_to": "message_id | null"
}
```

| 필드 | 설명 |
|---|---|
| `task_id` | 이 메시지가 속한 task. 일반 잡담/메시지는 `null`. |
| `content` | AI/사용자 발화 원문. **비신뢰 입력으로 취급** — 실행 가능한 명령으로 해석하지 않는다. |
| `content_hash` | watcher의 중복 트리거 감지에 사용. |
| `conclusion_tag` | AI가 결론에 도달했음을 표시하는 태그(예: `[FINAL_CONCLUSION]`). 없으면 `null`. |
| `needs_user_input` | AI가 스스로 "사용자 판단 필요"를 표시. |
| `in_reply_to` | 직전 어떤 메시지에 대한 응답인지(오실레이션 추적에도 사용 가능). |

### 예시

```json
{"schema_version":"1.0","room_id":"room-claude-codex-main","message_id":"3fa1...","task_id":"tk-20260625-001","sender":"user","timestamp":"2026-06-25T10:00:00+09:00","content":"종목 A 매수 신호 검토해줘","content_hash":"a1b2...","conclusion_tag":null,"needs_user_input":false,"in_reply_to":null}
```

## 스키마 B — 방 메타데이터 + Task + 세션 상태

경로: `chat_rooms/<room_id>/room_meta.json` (단일 파일, 갱신형 — atomic overwrite)

```json
{
  "schema_version": "1.0",
  "room_id": "room-claude-codex-main",
  "room_title": "Claude-Codex 토론방",
  "participants": ["user", "claude", "codex"],
  "created_at": "ISO8601",
  "last_active_at": "ISO8601",
  "tasks": [
    {
      "task_id": "tk-20260625-001",
      "title": "string",
      "status": "OPEN | IN_PROGRESS | WAITING_USER_DECISION | COMPLETED | CANCELLED",
      "opened_at": "ISO8601",
      "closed_at": "ISO8601 | null",
      "closed_by": "user | null",
      "round_count": 0
    }
  ],
  "session_state": {
    "claude": { "session_id": "string | null", "last_seen_message_id": "message_id | null" },
    "codex": { "session_id": "string | null", "last_seen_message_id": "message_id | null" }
  }
}
```

### Task 상태 전이

```
OPEN -> IN_PROGRESS <-> WAITING_USER_DECISION -> COMPLETED
                                               -> CANCELLED
```

- `IN_PROGRESS ⇄ WAITING_USER_DECISION`은 여러 번 오갈 수 있다(사용자가 추가 입력하면 다시 `IN_PROGRESS`).
- `COMPLETED`/`CANCELLED`는 **사용자만** 트리거한다 — AI는 이 전이를 일으킬 권한이 없다.

### session_state

각 AI의 CLI 세션 ID와 "마지막으로 본 메시지"를 영속화한다. 프로세스가 재시작돼도 멀티턴 컨텍스트와 진행 위치를 복구할 수 있게 하기 위함이다.

## 스키마 C — 호출/상태 로그

경로: `runtime_logs/<ai|system>/<YYYY-MM-DD>/call_*.log.jsonl` (JSON Lines, 한 줄 = 한 이벤트)

```json
{
  "schema_version": "1.0",
  "event_id": "uuid4",
  "room_id": "room-claude-codex-main | null",
  "task_id": "tk-20260625-001 | null",
  "session_id": "string | null",
  "source_workspace": "claude_codex_workspace | stock_workspace",
  "channel": "web | system | cli",
  "ai": "claude | codex | system",
  "event_type": "cli_call | status_change | task_assigned | error | heartbeat",
  "request_time": "ISO8601 | null",
  "completion_time": "ISO8601 | null",
  "duration_ms": "number | null",
  "retry_count": 0,
  "error": { "occurred": false, "type": null, "message": null },
  "process_meta": { "pid": "number | null", "cli_command": "string", "host": "string", "cwd": "string" }
}
```

`channel` 필드는 Phase 1에서는 `web | system | cli`만 쓰지만, Phase 2에서 `discord`가 추가되어도 기존 로그와 호환되도록 자유 문자열로 둔다.

## 두 스키마 간 연결

`room_id` + `task_id`로 스키마 A(대화 내용)와 스키마 C(호출/상태 이력)를 join할 수 있다.
