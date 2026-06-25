# cli_adapters/

claude/codex CLI를 세션 캡처·재개 방식으로 호출하는 래퍼가 들어갈 자리([`../../docs/STANDARD_RULES.md`](../../docs/STANDARD_RULES.md) 2.1 참조).

## 들어갈 것 (다음 단계)

- **Claude**: 첫 호출 `claude -p "<메시지>" --output-format json --dangerously-skip-permissions --append-system-prompt "<agent profile 본문>"` → 응답 JSON에서 `session_id` 캡처. 다음 호출부터 `claude -p "<새 메시지>" --resume <session_id> --output-format json`.
- **Codex**: 첫 호출 `codex exec --no-alt-screen --yolo -c developer_instructions="<agent profile 본문>" "<메시지>"` → 세션 ID는 `~/.codex/sessions/YYYY/MM/DD/`의 최신 파일에서 확인. 다음 호출부터 `codex exec resume <session_id> "<새 메시지>"`.
- 두 CLI 모두 정확한 플래그명은 버전에 따라 다를 수 있으므로, 구현 시작 전 `claude --help` / `codex exec --help`로 재확인한다.
- Windows에서 `.cmd` 셔임 해석, OAuth 컨텍스트 보존 등 주의사항은 [`../../docs/STANDARD_RULES.md`](../../docs/STANDARD_RULES.md) 2.5 참조.

## 이번 범위 아님

실제 subprocess 호출 코드는 다음 단계에서 작성한다.
