# stock_pjt_ai

Claude와 Codex 두 AI를 활용한 개인용 자동화/분석 프로젝트 모음. 이 레포는 두 개의 독립 프로젝트와, 둘이 공용으로 쓰는 인프라로 구성된다.

## 구성

| 경로 | 설명 | 상태 |
|---|---|---|
| `claude_codex_workspace/` | 사용자·Claude·Codex가 하나의 채팅방(Room)에서 대화하며 토론·리뷰하는 자동화 도구 | Phase 1, 골격+표준 룰만 |
| `stock_workspace/` | AI 기반 주식 분석 프로젝트 | 경량 골격만, 설계 예정 |
| `chat_rooms/` | 두 워크스페이스 공유 — 방 단위 대화 아카이브 (JSON) | 골격 |
| `runtime_logs/` | 두 워크스페이스 공유 — AI 호출/상태 로그 (JSON) | 골격 |

## 핵심 개념

- **Room(방)**: 카카오톡 채팅방처럼 항상 열려 있는 영속적 대화 공간. 사용자·Claude·Codex가 함께 있다.
- **Task(요청)**: 방 안에서 발생하는 개별 요청. 여러 라운드에 걸쳐 이어질 수 있고, 사용자가 완료로 판단해야만 종료된다.

자세한 설계는 [`docs/STANDARD_RULES.md`](docs/STANDARD_RULES.md)를 참조.

## 로드맵

- **Phase 1 (현재)**: 자체 웹 UI로 방 상태를 확인하는 pull 방식. `claude_codex_workspace`부터 적용.
- **Phase 2 (추후)**: Discord 연동(푸시 알림/원격 지시), 외부 접속용 별도 서버, `stock_workspace` 확장.
