"""휴장일 캘린더(config.market_calendar) + is_trading_day 단위 테스트"""

from datetime import date

from config.market_calendar import is_market_holiday
from scheduler.tasks import is_trading_day


class TestIsMarketHoliday:
    def test_known_2026_holidays(self):
        assert is_market_holiday(date(2026, 1, 1)) is True  # 신정
        assert is_market_holiday(date(2026, 2, 17)) is True  # 설날
        assert is_market_holiday(date(2026, 12, 25)) is True  # 성탄절

    def test_regular_weekday_is_not_holiday(self):
        assert is_market_holiday(date(2026, 6, 24)) is False  # 수요일, 평범한 거래일

    def test_unregistered_year_returns_false(self):
        assert is_market_holiday(date(2099, 1, 1)) is False


class TestIsTradingDay:
    def test_weekend_is_not_trading_day(self):
        assert is_trading_day(date(2026, 6, 27)) is False  # 토요일

    def test_holiday_weekday_is_not_trading_day(self):
        assert is_trading_day(date(2026, 1, 1)) is False  # 목요일, 신정

    def test_regular_weekday_is_trading_day(self):
        assert is_trading_day(date(2026, 6, 24)) is True  # 수요일
