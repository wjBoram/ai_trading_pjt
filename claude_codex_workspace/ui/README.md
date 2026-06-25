# ui/

자체 웹 대시보드(Phase 1, pull 방식)가 들어갈 자리. 사용자가 직접 열어서 방 타임라인과 task 상태 뱃지를 확인한다. 프레임워크(Streamlit/Flask/FastAPI+HTML 등)는 구현 단계에서 결정한다.

## 들어갈 것 (다음 단계)

- 방 목록 + 타임라인 뷰어 (`chat_rooms/<room_id>/...` 읽기).
- task 상태 뱃지 (`WAITING_USER_DECISION`일 때 강조).
- 사용자 액션: 메시지 전송(새 task 생성/합류), task 완료 처리, task 취소.

## 이번 범위 아님

실제 구현 코드는 다음 단계에서 작성한다.
