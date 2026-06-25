# 용어집

NanoClaw, cli-agent-orchestrator(CAO), claude_codex_bridge(CCB) 세 레퍼런스 프로젝트 분석을 바탕으로, 우리 프로젝트에 필요한 부분만 채택하거나 단순화해 정의한 용어다.

| 용어 | 정의 | 출처/근거 |
|---|---|---|
| **Room(방)** | 사용자·Claude·Codex가 항상 함께 있는 영속적 채팅 공간. 모든 발화가 한 타임라인에 쌓인다. | 사용자 정의(카카오톡 채팅방 모델) |
| **Task(요청)** | 방 안에서 발생하는 개별 요청. 여러 라운드에 걸쳐 이어질 수 있고, 사용자 판단으로만 종료된다. | 사용자 정의 |
| **Provider** | CLI 도구의 추상화 계층(`claude`, `codex`). | CAO에서 차용 |
| **Agent Profile** | AI 참가자의 역할/페르소나/실행 옵션을 정의한 마크다운(+YAML frontmatter) 파일. | CAO `agent-profile.md` 패턴 차용 |
| **Continuation / Session ID** | CLI의 멀티턴 세션 재개 토큰. Claude/Codex 모두 `--resume`/`resume` 플래그로 구현된다. | NanoClaw의 개념을 CLI 플래그로 재구현 |
| **단일 작성자 원칙(Single-writer)** | 방마다 그 방을 담당하는 오케스트레이터 1개만 해당 방의 파일을 쓴다. AI CLI는 직접 파일을 쓰지 않는다. | NanoClaw의 듀얼 SQLite 분리 원칙을 단순화 |
| **단방향 컨텍스트 전달** | A의 메시지를 B의 세션에 주입할 때 A 자신의 세션은 건드리지 않는다. | CCB `ctx-transfer` 원칙 채택 |
| **Async Guardrail** | 한 AI를 호출하는 동안 다른 AI를 동시에 호출하지 않고, AI가 서로의 응답을 스스로 polling하지 않는다 — 그 역할은 항상 오케스트레이터가 한다. | CCB 핵심 규칙 채택 |
| **needs_user_input** | AI가 스스로 "사용자 판단 필요"를 표시하는 메시지 필드. | 사용자 요구사항 기반 자체 설계 |
| **Pull 방식** | 사용자가 직접 웹 대시보드를 열어서 상태를 확인하는 방식(Phase 1). 푸시 알림과 대비된다. | 사용자 정의 |
| **Phase 1 / Phase 2** | Phase 1 = 자체 웹 UI, pull 방식, Docker/tmux 없음. Phase 2(추후) = Discord 연동, 외부 서버. | 사용자 결정 |

## 참고했지만 이번엔 채택하지 않은 용어 (CAO/CCB)

이 항목들은 CAO/CCB에 존재하지만, 우리 스코프(AI 2개, 자체 웹 UI, raw 터미널 미노출)에는 해당하지 않아 이번 표준 룰에는 포함하지 않았다. 향후 더 복잡한 멀티 에이전트 오케스트레이션이 필요해지면 참고할 수 있다.

| 용어 | CAO/CCB에서의 의미 | 채택하지 않은 이유 |
|---|---|---|
| **Handoff / Assign** | 슈퍼바이저가 워커에게 동기/비동기로 작업을 위임 | 우리는 항상 2개의 고정된 AI가 한 방에 있어 위임 구조가 불필요 |
| **Control Plane** | Web UI / CLI / MCP 서버 등 다중 관리 인터페이스 | Phase 1은 웹 UI 하나로 충분 |
| **tmux 터미널 puppeteering** | 실제 터미널 pane을 띄우고 키 입력/출력을 스크래핑 | Claude/Codex CLI가 비대화형 세션 재개를 지원하고, raw 터미널을 노출할 필요가 없어 더 단순한 subprocess 방식 채택 |
