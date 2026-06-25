# watcher/

방 상태 변화를 보고 다음 행동을 결정하는 트리거 진입점이 들어갈 자리. 상시 폴 루프가 아니라, 웹 백엔드가 사용자의 메시지 전송 액션을 받았을 때 호출되는 진입점으로 가볍게 설계한다([`../../docs/STANDARD_RULES.md`](../../docs/STANDARD_RULES.md) 2.4 참조).

## 들어갈 것 (다음 단계)

- 방의 `messages.jsonl`/`room_meta.json`을 읽고, 다음에 누구(Claude/Codex/사용자 대기)가 행동해야 하는지 판정하는 함수.
- `content_hash` 기반 중복 트리거 감지.
- Phase 2에서 Discord 등 외부 채널 이벤트도 이 진입점을 통하도록 확장.

## 이번 범위 아님

실제 구현 코드는 다음 단계에서 작성한다.
