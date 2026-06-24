"""대화 컨텍스트 저장 스크립트

새 AI 세션 요약을 conversations/sessions/ 에 저장합니다.
사용법:
    python scripts/save_context.py
    python scripts/save_context.py --date 2026-06-24 --num 002
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


def get_next_session_num(sessions_dir: Path, target_date: str) -> str:
    existing = list(sessions_dir.glob(f"{target_date}_*.md"))
    if not existing:
        return "001"
    nums = []
    for f in existing:
        parts = f.stem.split("_")
        if len(parts) >= 2:
            try:
                nums.append(int(parts[-1]))
            except ValueError:
                pass
    return f"{max(nums) + 1:03d}" if nums else "001"


def create_session_file(sessions_dir: Path, session_date: str, session_num: str) -> Path:
    filename = f"{session_date}_{session_num}.md"
    filepath = sessions_dir / filename

    content = f"""---
date: {session_date}
session_id: "{session_num}"
version_range: "vX.X.X → vX.X.X"
topics:
  - (작업 주제를 입력하세요)
---

## 주요 작업 내용

(이번 세션에서 수행한 작업을 기술하세요)

---

## 결정된 사항

| 결정 | 이유 |
|------|------|
| | |

---

## 구현·수정된 파일

- `경로/파일명`: 변경 내용

---

## 미결 사항 / 다음 세션 작업

- [ ]

---

## 참고 컨텍스트

- **작업 브랜치**: main
- **관련 이슈**:
"""

    filepath.write_text(content, encoding="utf-8")
    return filepath


def update_sessions_index(conversations_dir: Path, session_date: str, session_num: str, summary: str) -> None:
    index_path = conversations_dir / "SESSIONS.md"
    if not index_path.exists():
        return

    text = index_path.read_text(encoding="utf-8")

    new_row = f"| {session_date} | [{session_num}](sessions/{session_date}_{session_num}.md) | | {summary} |"

    marker = "| 날짜 | 세션 | 버전 | 주요 작업 |"
    sep = "|------|------|------|---------|"

    if marker in text and sep in text:
        insert_after = text.index(sep) + len(sep)
        text = text[:insert_after] + "\n" + new_row + text[insert_after:]
        index_path.write_text(text, encoding="utf-8")
        print(f"SESSIONS.md 인덱스 업데이트 완료")


def main() -> None:
    parser = argparse.ArgumentParser(description="대화 컨텍스트 세션 파일 생성")
    parser.add_argument("--date", default=str(date.today()), help="세션 날짜 (YYYY-MM-DD, 기본: 오늘)")
    parser.add_argument("--num", default=None, help="세션 번호 (001, 002, ... 기본: 자동)")
    parser.add_argument("--summary", default="(요약 없음)", help="세션 요약 (SESSIONS.md 인덱스용)")
    args = parser.parse_args()

    root = Path(__file__).parent.parent
    sessions_dir = root / "conversations" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    session_num = args.num or get_next_session_num(sessions_dir, args.date)

    filepath = create_session_file(sessions_dir, args.date, session_num)
    print(f"세션 파일 생성: {filepath}")

    update_sessions_index(root / "conversations", args.date, session_num, args.summary)
    print(f"\n다음 작업: {filepath} 파일을 열어 내용을 채우세요.")
    print(f"또는 Claude Code에게: '이번 세션 내용을 {filepath.name}에 저장해줘'")


if __name__ == "__main__":
    main()
