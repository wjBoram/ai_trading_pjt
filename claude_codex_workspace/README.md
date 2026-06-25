# claude_codex_workspace

사용자·Claude·Codex가 하나의 영속적인 채팅방(Room)에서 함께 대화하는 자동화 도구. AI 둘은 서로 토론·리뷰하고, 사용자 판단이 필요하면 사용자를 부르며, 그 방의 모든 대화가 영구 보존된다.

표준 룰/스키마/용어집은 레포 루트의 [`../docs/`](../docs/) 참조. 이 프로젝트는 그 표준을 구현하는 코드가 들어갈 자리다.

## 범위

- **Phase 1 (현재)**: 자체 웹 UI로 방 상태를 확인하는 pull 방식. Native Windows subprocess로 Claude/Codex CLI를 세션 재개 방식으로 호출.
- **Phase 2 (다음, 이번 범위 아님)**: Discord 연동, 외부 접속용 별도 서버.

## 하위 디렉토리

| 디렉토리 | 역할 |
|---|---|
| `agent_profiles/` | AI별 역할/페르소나 정의 (마크다운+YAML) |
| `watcher/` | 방 상태 변화를 보고 다음 행동을 결정하는 트리거 진입점 |
| `orchestrator/` | 다음 발화자 판정, task 상태 전이, 세션 push 로직 |
| `ui/` | 자체 웹 대시보드 (Phase 1) |
| `cli_adapters/` | claude/codex CLI 세션 캡처·재개 래퍼 |

## 현재 상태

골격과 표준 룰 문서만 존재한다. 실제 코드는 아직 구현되지 않았다(다음 단계).
