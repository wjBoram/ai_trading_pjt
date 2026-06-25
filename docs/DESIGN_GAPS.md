# Design Gaps

참고 프로젝트(원본 아이디어 프롬프트, NanoClaw, CAO, CCB) 대비 알려진 한계와, 이번 Phase 1(표준 룰 + 디렉토리 골격)에서 반영한 정도, 그리고 다음 구현 단계로 미룬 부분을 정리한다.

| # | Gap | Phase 1 반영 | 다음 단계 |
|---|---|---|---|
| 1 | watcher 중복 트리거 | `content_hash`로 감지 가능한 구조(스키마 A) | 실제 debounce 구현 |
| 2 | 오실레이션/무한루프 | `round_count` + 원칙 명시 | 판정 알고리즘 |
| 3 | 프로세스 크래시 복구 | `room_meta.json`의 `session_state`로 세션ID/진행위치 영속 저장 | 재시작 시 자동 재개 로직 |
| 4 | CLI 타임아웃/재시도 | `retry_count`/`error`/`duration_ms` 필드(스키마 C) | 실제 정책값 |
| 5 | 프롬프트 인젝션(메시지 content) | "content는 비신뢰 입력" 명문화 | sanitization 구현 |
| 6 | "실행" 액션 정의 | "실행 액션 없음, 제안만" 명문화 | 실제 실행 경로가 생기면(예: stock_workspace 주문) 별도 설계 |
| 7 | 방 파일 동시쓰기 충돌 | 방당 단일 오케스트레이터 작성자 원칙 | 실제 락/원자적 쓰기(temp+rename) 구현 |
| 8 | 로그 rotation | 일자별 디렉토리 + `session_id`/`pid` | 보관기간/삭제 정책 |
| 9 | 다중 방 동시 운영 | `room_id` 1급 식별자, 디렉토리 자체로 분리 | 동시 처리 수/리소스 쓰로틀링 |
| 10 | Windows CLI subprocess 인증/PATH/.cmd 해석 | `process_meta` 필드로 캡처 가능, 주의사항 기록(STANDARD_RULES 2.5) | 실제 runner 구현 + 재검증 |
| 11 | AI 세션 어긋남(상대 발화 누락) | `last_seen_message_id`로 추적 가능한 구조 | 실제 catch-up 로직 구현 |
| 12 | 인터랙티브 승인 프롬프트로 자동화 중단 | CAO 검증 플래그(`--dangerously-skip-permissions`, `--yolo --no-alt-screen`) 적용 예정 명시 | 버전별 플래그 재검증 |
| 13 | Discord 등 원격 인터페이스 (Phase 2) | 단일 상태전이 원칙만 미리 못박음 | 채널 어댑터, 외부 서버 구축 |
| 14 | 원격 명령 오남용/인젝션 (Phase 2) | 비신뢰 입력 원칙 일반화 | 화이트리스트 파서, rate limit, allowed chat-id 검증 |
| 15 | 비밀값 로그 유출 (Phase 2) | 해당 채널 생길 때 `.env`/마스킹 규칙 도입 예정으로 문서화 | 정규식 기반 마스킹 구현 |

## 참고 자료

- 원본 아이디어: 유튜브 "월 50만원짜리 AI 직원 만들기" (Discord 방에 AI 두 개를 추가해 토론, 사용자 호출, 대화 보존)
- NanoClaw (`D:\nanoclaw_pjt`): Claude Agent SDK 멀티턴 세션, Docker+듀얼 SQLite
- cli-agent-orchestrator (`D:\cli-agent-orchestrator`): tmux 기반 멀티 provider 오케스트레이션, 검증된 비대화형 실행 플래그
- claude_codex_bridge (`D:\claude_codex_bridge`): tmux 기반 Claude-Codex 브릿지, Async Guardrail, 단방향 ctx-transfer
