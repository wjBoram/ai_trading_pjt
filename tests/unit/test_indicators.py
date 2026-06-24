"""indicators.technical 모듈 단위 테스트"""

from datetime import date, timedelta

import pandas as pd

from indicators.technical import calculate_indicators, get_latest_indicators


def _make_ohlcv(rows: int = 70) -> pd.DataFrame:
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(rows)]
    closes = [70000 + i * 100 + (i % 3 - 1) * 200 for i in range(rows)]
    return pd.DataFrame(
        {
            "date": dates,
            "open": [c - 300 for c in closes],
            "high": [c + 500 for c in closes],
            "low": [c - 500 for c in closes],
            "close": closes,
            "volume": [1_000_000 + i * 10000 for i in range(rows)],
        }
    )


class TestCalculateIndicators:
    def test_adds_quant_factor_columns(self):
        df = calculate_indicators(_make_ohlcv())
        assert "return_60d" in df.columns
        assert "disparity_ema20" in df.columns

    def test_return_60d_is_pct_change_over_60_periods(self):
        df = calculate_indicators(_make_ohlcv())
        last = df.iloc[-1]
        expected = df["close"].iloc[-1] / df["close"].iloc[-61] - 1
        assert last["return_60d"] == expected

    def test_disparity_ema20_close_to_100_for_flat_trend(self):
        df = calculate_indicators(_make_ohlcv())
        last = df.iloc[-1]
        # 완만한 상승 추세 데이터이므로 이격도가 100 근처(과도하게 벗어나지 않음)
        assert 90 < last["disparity_ema20"] < 110


class TestGetLatestIndicators:
    def test_whitelist_includes_new_columns(self):
        result = get_latest_indicators(_make_ohlcv())
        assert result is not None
        assert "return_60d" in result
        assert "disparity_ema20" in result
        assert result["return_60d"] is not None
        assert result["disparity_ema20"] is not None
