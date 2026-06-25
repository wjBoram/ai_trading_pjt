# agent_profiles/

방에 참여하는 각 AI의 역할/페르소나/실행 옵션을 마크다운(+YAML frontmatter)으로 정의하는 자리. 코드에 프롬프트를 하드코딩하지 않기 위함이다(CAO의 agent-profile 패턴 채택, [`../../docs/STANDARD_RULES.md`](../../docs/STANDARD_RULES.md) 2.2 참조).

## 들어갈 것 (다음 단계)

- `claude.md` — `name: claude`, `provider: claude_code`, `permissionMode`, 시스템 프롬프트 본문.
- `codex.md` — `name: codex`, `provider: codex_cli`, 시스템 프롬프트 본문.

## 이번 범위 아님

실제 프로필 파일과 이를 읽어 CLI 호출에 주입하는 코드는 다음 단계에서 작성한다.
