# 표준 룰 (Phase 1)

이 문서는 `claude_codex_workspace`와 `stock_workspace`가 공유하는 인프라(`chat_rooms/`, `runtime_logs/`)와 AI 협업 방식에 대한 표준을 정의한다. 각 워크스페이스 내부의 구체적인 업무 로직(예: 주식 분석 알고리즘)은 다루지 않는다.

이번 Phase 1의 적용 범위는 `claude_codex_workspace`로 한정한다. `stock_workspace`는 빈 골격만 두고 상세 설계는 다음 단계에서 진행한다.

## 1. 핵심 개념: Room(채팅방)과 Task(요청)

- **Room**: 사용자·Claude·Codex가 함께 있는 영속적 채팅 공간. 카카오톡 채팅방처럼 한 번 만들어지면 계속 유지되며, 모든 발화(사용자/Claude/Codex/시스템)가 시간순으로 한 타임라인에 쌓인다. `room_id`로 식별한다.
- **Task**: 방 안에서 발생하는 개별 요청 단위. 하나의 task는 여러 라운드(AI 응답 ⇄ 사용자 추가 입력)에 걸쳐 이어질 수 있고, **사용자가 완료로 판단해야만 종료**된다. `task_id`로 식별한다.
- **관계**: 한 Room 안에 여러 Task가 시간차로 생성될 수 있다. 방은 닫히지 않고, task만 열리고 닫힌다. 일반 대화는 `task_id = null`로 방 타임라인에 남을 수 있다.
- **동작 흐름**: 사용자가 방에 메시지(요청)를 보냄 → 새 task 생성 또는 기존 진행 중 task에 합류 → 오케스트레이터가 다음 차례 AI를 판정해 그 AI의 세션에 메시지를 push → AI 응답을 같은 방에 기록 → 결론에 도달하거나 AI가 판단 필요를 표시하면 task 상태를 `WAITING_USER_DECISION`으로 전이 → 사용자가 웹에서 확인 후 추가 지시(`IN_PROGRESS`로 복귀) 또는 완료 처리(`COMPLETED`).

## 2. 실행 방식: Claude/Codex CLI 대화형(멀티턴) 호출

WSL2/tmux 없이, Native Windows Python subprocess + 각 CLI의 세션 재개 플래그를 사용한다(자체 웹 UI가 화면 역할을 하므로 raw 터미널을 사용자에게 보여줄 필요가 없고, 두 CLI 모두 비대화형 세션 재개를 정식 지원하기 때문).

### 2.1 세션 캡처·재개 + 비대화형 실행 플래그

- **Claude**: 첫 호출 `claude -p "<메시지>" --output-format json --dangerously-skip-permissions --append-system-prompt "<agent profile 본문>"` → 응답 JSON에서 `session_id` 캡처. 다음 호출부터 `claude -p "<새 메시지>" --resume <session_id> --output-format json`.
- **Codex**: 첫 호출 `codex exec --no-alt-screen --yolo -c developer_instructions="<agent profile 본문>" "<메시지>"` → 세션 ID는 `~/.codex/sessions/YYYY/MM/DD/`의 최신 파일에서 확인. 다음 호출부터 `codex exec resume <session_id> "<새 메시지>"` (또는 `resume --last`).
- `--dangerously-skip-permissions`(Claude), `--yolo --no-alt-screen`(Codex)은 인터랙티브 승인 프롬프트로 자동화가 막히는 것을 방지하기 위한 플래그다. 정확한 플래그명/동작은 설치된 버전에 따라 다를 수 있으므로 구현 단계에서 `--help`로 재확인한다.

### 2.2 Agent Profile — AI별 역할/페르소나 정의

코드에 프롬프트를 하드코딩하지 않고, 방의 각 AI 참가자를 마크다운(+YAML frontmatter) 프로필 파일로 정의한다.

```markdown
---
name: claude
provider: claude_code
permissionMode: bypassPermissions
---
당신은 Claude이며, 사용자와 다른 AI(Codex)가 함께 있는 채팅방에 참여 중입니다...
```

저장 위치: `claude_codex_workspace/agent_profiles/claude.md`, `claude_codex_workspace/agent_profiles/codex.md`. 본문은 `--append-system-prompt`(Claude) / `developer_instructions`(Codex)로 주입된다.

### 2.3 세션 분리 + 단방향 컨텍스트 전달 + 비동기 경계

- Claude와 Codex는 각자 독립된 세션(`session_id`)을 가진다.
- 누군가(사용자 또는 한 AI)가 방에 메시지를 남기면, 오케스트레이터는 그 메시지를 **상대 AI의 세션에만** 다음 입력으로 push한다 — 발신자 자신의 세션은 건드리지 않는다(단방향 컨텍스트 전달).
- 각 AI의 `session_state`에 `last_seen_message_id`를 기록해, 다음 호출 시 아직 못 본 메시지만 모아 프롬프트에 포함한다.
- **Async Guardrail**: 오케스트레이터가 한 AI를 호출하는 동안 다른 AI는 절대 동시에 호출되지 않는다. 한 AI의 CLI 호출은 항상 완료까지 기다리는 하나의 유한한 턴이며, AI가 다른 AI의 응답을 스스로 기다리며 polling하는 코드는 작성하지 않는다 — 그 역할은 항상 오케스트레이터가 한다.

### 2.4 트리거 방식

상시 폴 루프 대신, 웹 백엔드가 사용자의 메시지 전송 액션을 받으면 오케스트레이터 함수를 그 자리에서(또는 백그라운드 스레드로) 동기 실행하고, AI 응답 라운드를 정지 조건(결론/판단필요/라운드제한)까지 반복한 뒤 리턴한다. `watcher/`는 "방 상태를 보고 다음 행동을 결정하는 트리거 진입점"으로 가볍게 정의하며, Phase 2에서 Discord 등 외부 채널이 추가되면 그쪽 이벤트도 같은 진입점을 호출한다.

### 2.5 Windows 실행 주의사항 (재검증 필요)

- Windows에서 `claude`/`codex`는 `.cmd` 셔임으로 해석되는 경우가 있어 `subprocess`에서 `shell=True` 또는 `.cmd` 확장자를 명시해야 하는 경우가 있다.
- 일부 플래그가 OAuth 인증 컨텍스트를 깨뜨린 사례가 있었다 — 인증이 필요한 호출 경로에서는 최소 플래그만 사용한다.
- 이 항목들은 구현 단계에서 재검증이 필요하다.

## 3. 디렉토리 맵

```
D:\stock_pjt_ai\
├── CLAUDE.md / AGENTS.md / README.md
├── docs\                      표준 룰, 스키마, 용어집, gap 목록
├── chat_rooms\                공유 — 방 단위 대화 아카이브
├── runtime_logs\              공유 — 호출/상태/실시간 로그
├── claude_codex_workspace\    Claude-Codex 채팅방 자동화 도구
└── stock_workspace\           주식 분석 프로젝트
```

## 4. 명명 규칙

- `room_id`: `room-<kebab-slug>` (예: `room-claude-codex-main`)
- `task_id`: `tk-<YYYYMMDD>-<3자리seq>` (예: `tk-20260625-001`)
- 메시지 로그: `chat_rooms/<room_id>/<YYYY-MM-DD>/messages.jsonl`
- 방 메타/task/세션 인덱스: `chat_rooms/<room_id>/room_meta.json`
- **단일 작성자 원칙**: 방마다 그 방을 담당하는 오케스트레이터(또는 그 방을 다루는 단일 함수 호출 컨텍스트) 1개만 `messages.jsonl`/`room_meta.json`을 쓴다. Claude/Codex CLI는 stdout만 반환하고, 실제 파일 기록은 항상 오케스트레이터가 한다.

상세 JSON 스키마는 [`JSON_SCHEMAS.md`](JSON_SCHEMAS.md), 용어는 [`GLOSSARY.md`](GLOSSARY.md) 참조.

## 5. AI 직원 운영 모델

### 5.1 Phase 1 (이번 범위)

1. 사용자가 방에 메시지(요청)를 보냄 → 새 task 또는 진행 중 task에 연결 → 오케스트레이터가 다음 차례 AI를 판정해 그 AI 세션에 push → 응답을 같은 방에 기록.
2. **자동 승인/종료 금지**: AI는 `COMPLETED`/`CANCELLED`로 전이할 권한이 없다.
3. **사용자 호출 조건**: (a) AI가 결론 태그를 냄, (b) 라운드 제한 도달, (c) AI가 스스로 `needs_user_input`을 표시.
4. **이어지는 대화**: 사용자가 그 task에 추가 입력을 보내면 `IN_PROGRESS`로 복귀하고 라운드 카운트가 증가한다. 방은 항상 열려 있다.
5. **Pull 방식 확인**: 웹 대시보드를 열면 방 타임라인과 task 상태 뱃지가 보인다. 푸시 알림은 없다.
6. **격리(경량판)**: Docker 없이, 워크스페이스별 독립 디렉토리 + 독립 `CLAUDE.md`/`AGENTS.md`. 방마다 단일 작성자 원칙으로 동시쓰기 충돌을 구조적으로 차단한다.

### 5.2 Phase 2 (추후 확장 — 이번 구현 범위 아님)

- Discord 채널 어댑터: 방의 상태 전이(`WAITING_USER_DECISION`)를 Discord 멘션으로 푸시, 화이트리스트 명령으로 원격 메시지 전송.
- 외부 접속용 별도 서버 구축.
- 미리 해둘 것: "task 종료는 사용자만", 단일 작성자 원칙, Async Guardrail을 그대로 재사용 — 채널이 늘어나도 같은 상태 전이 함수를 거치게 한다.

## 6. 알려진 한계와 다음 단계

[`DESIGN_GAPS.md`](DESIGN_GAPS.md) 참조.
