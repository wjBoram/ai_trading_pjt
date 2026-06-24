# 세션 인덱스

AI 대화 세션 목록. 최신 세션이 위에 위치합니다.

---

| 날짜 | 세션 | 버전 | 주요 작업 |
|------|------|------|---------|
| 2026-06-23 | [001](sessions/2026-06-23_001.md) | v1.0.0 → v1.1.0 | 프로젝트 최초 설계·구현, 실시간 갱신 시스템, 대화 저장소 구축 |

---

## 현재 프로젝트 상태 (최종 업데이트: 2026-06-23)

| 항목 | 내용 |
|------|------|
| 버전 | v1.1.0 |
| Python | 3.13 |
| Phase | Phase 1-2 완료, Phase 3(KIS 실거래) 예정 |
| DB | SQLite WAL 모드 (data_store/trading.db) |
| 거래 모드 | paper (기본값) |
| 테스트 | 22개 단위 테스트 (tests/unit/test_agents.py) |

## 핵심 미결 사항

- [ ] KIS OpenAPI 실거래 연동 (`data/kis_client.py`)
- [ ] KIS WebSocket 실시간 시세
- [ ] 백테스트 스크립트 (`scripts/backtest.py`)
- [ ] 단위 테스트 커버리지 80%+ 달성 (현재 agents/risk_manager 집중)
