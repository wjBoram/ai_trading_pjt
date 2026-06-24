# 대화 컨텍스트 저장소

이 디렉토리는 AI와의 개발 대화 세션 기록을 저장합니다.
새 Claude Code 세션을 시작할 때 이 디렉토리를 참조하면 이전 대화에서 이어서 작업할 수 있습니다.

---

## 디렉토리 구조

```
conversations/
├── README.md            # 이 파일 — 사용법
├── SESSIONS.md          # 세션 인덱스 (날짜별 목록)
└── sessions/
    └── YYYY-MM-DD_NNN.md  # 개별 세션 파일
```

---

## 세션 파일 명명 규칙

```
sessions/YYYY-MM-DD_NNN.md
```
- `YYYY-MM-DD`: 세션 날짜
- `NNN`: 같은 날 세션 번호 (001, 002, ...)

---

## 새 세션 시작 시 AI에게 제공하는 프롬프트

```
이 프로젝트를 이어서 개발하려 합니다.
CLAUDE.md와 conversations/SESSIONS.md를 먼저 읽어서 
지금까지의 컨텍스트를 파악한 뒤 작업을 진행해주세요.
```

---

## 세션 파일 수동 생성

```bash
python scripts/save_context.py --date 2026-06-23 --summary "작업 내용 요약"
```

또는 Claude Code에게 직접 요청:
```
현재 대화 내용을 conversations/sessions/ 에 저장해줘.
```

---

## 세션 파일 형식 (템플릿)

```markdown
---
date: YYYY-MM-DD
session_id: NNN
version_range: "[시작 버전] → [종료 버전]"
topics: [주제1, 주제2]
---

## 주요 작업 내용

## 결정된 사항

## 구현·수정된 파일

## 미결 사항 / 다음 세션 작업

## 참고 컨텍스트
```

---

## AI 자동 컨텍스트 로딩 순서

Claude Code CLI가 이 프로젝트를 열면 자동으로 로드되는 파일:

1. `CLAUDE.md` — 프로젝트 전체 컨텍스트 (자동 로드)
2. `conversations/SESSIONS.md` — 세션 인덱스 (수동 참조 요청)
3. `conversations/sessions/<최신>.md` — 마지막 세션 상세 (수동 참조 요청)
