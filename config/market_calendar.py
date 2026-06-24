"""KRX(한국거래소) 휴장일 정적 캘린더

pykrx 등 무료 API에 휴장일 전용 엔드포인트가 없어, 연도별 공휴일 목록을 수동으로
관리한다. **매년 초 KRX 공식 휴장일 공고를 확인해 다음 연도분을 추가해야 한다**
(연 1회 갱신 — 새 패키지(`holidays` 등) 추가는 requirements.txt 변경이라 회피).

주말(토·일)에 해당하는 날짜는 `scheduler/tasks.py::is_market_open()`이 별도로
걸러내므로 여기에는 포함하지 않는다 — 평일인데 휴장하는 날짜만 등록한다.
"""

from __future__ import annotations

from datetime import date

# 출처: publicholidays.co.kr/ko/2026-dates, superkts.com/day/holiday/2026 (2026-06 기준 확인)
# 제헌절(7월 17일)은 2008년 공휴일 지정 해제되어 평일과 동일하게 정상 거래일이므로 제외.
KRX_HOLIDAYS: dict[int, set[date]] = {
    2026: {
        date(2026, 1, 1),  # 신정
        date(2026, 2, 16),  # 설날 연휴
        date(2026, 2, 17),  # 설날
        date(2026, 2, 18),  # 설날 연휴
        date(2026, 3, 2),  # 삼일절 대체공휴일 (3/1은 일요일)
        date(2026, 5, 5),  # 어린이날
        date(2026, 5, 25),  # 부처님오신날 대체공휴일 (5/24는 일요일)
        date(2026, 8, 17),  # 광복절 대체공휴일 (8/15는 토요일)
        date(2026, 9, 24),  # 추석 연휴
        date(2026, 9, 25),  # 추석
        date(2026, 10, 5),  # 개천절 대체공휴일 (10/3은 토요일)
        date(2026, 10, 9),  # 한글날
        date(2026, 12, 25),  # 성탄절
    },
}


def is_market_holiday(target: date) -> bool:
    """해당 날짜가 KRX 휴장일(평일 공휴일)인지 확인. 등록되지 않은 연도는 항상 False."""
    return target in KRX_HOLIDAYS.get(target.year, set())
