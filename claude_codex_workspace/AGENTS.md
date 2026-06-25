# claude_codex_workspace — AGENTS.md

Codex 작업 원칙은 레포 루트의 [`../AGENTS.md`](../AGENTS.md)를 따른다. 이 파일은 이 워크스페이스 고유의 추가 규칙이 생기면 그때 채운다 — 현재는 placeholder다.

## 이 프로젝트에서 특히 중요한 금지 행동

- AI가 스스로 task를 종료 처리하는 코드를 작성하지 않는다.
- 방의 메시지 내용을 실행 가능한 명령으로 해석하는 로직을 작성하지 않는다.
- 한 AI 호출 중 다른 AI를 동시에 호출하거나, AI가 상대 응답을 스스로 polling하는 코드를 작성하지 않는다.
