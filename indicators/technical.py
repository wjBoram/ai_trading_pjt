"""기술적 지표 계산 (ta 라이브러리)"""

from typing import Optional

import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """OHLCV DataFrame에 기술 지표 컬럼 추가

    입력 columns: date, open, high, low, close, volume
    출력 추가 columns: rsi, macd, macd_signal, macd_hist,
                      bb_upper, bb_mid, bb_lower, ema5, ema20, ema60,
                      atr, volume_ratio, stoch_k, stoch_d,
                      return_1d, return_5d, return_20d, return_60d,
                      disparity_ema20
    """
    try:
        import ta
    except ImportError as e:
        raise ImportError("pip install ta 필요") from e

    if df is None or len(df) < 20:
        logger.warning("지표 계산 불가 - 데이터 부족", rows=len(df) if df is not None else 0)
        return df

    df = df.copy().sort_values("date").reset_index(drop=True)

    # RSI(14)
    df["rsi"] = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()

    # MACD(12,26,9)
    macd_indicator = ta.trend.MACD(close=df["close"], window_slow=26, window_fast=12, window_sign=9)
    df["macd"] = macd_indicator.macd()
    df["macd_signal"] = macd_indicator.macd_signal()
    df["macd_hist"] = macd_indicator.macd_diff()

    # Bollinger Bands(20,2)
    bb = ta.volatility.BollingerBands(close=df["close"], window=20, window_dev=2)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_mid"] = bb.bollinger_mavg()
    df["bb_lower"] = bb.bollinger_lband()

    # EMA
    df["ema5"] = ta.trend.EMAIndicator(close=df["close"], window=5).ema_indicator()
    df["ema20"] = ta.trend.EMAIndicator(close=df["close"], window=20).ema_indicator()
    df["ema60"] = ta.trend.EMAIndicator(close=df["close"], window=60).ema_indicator()

    # 이격도 (EMA20 대비, 퀀트 팩터: 평균회귀/과매수과매도 보조지표) - 100=평균과 동일
    df["disparity_ema20"] = df["close"] / df["ema20"] * 100

    # ATR(14) - 정규화
    df["atr"] = ta.volatility.AverageTrueRange(
        high=df["high"], low=df["low"], close=df["close"], window=14
    ).average_true_range()
    df["atr_pct"] = df["atr"] / df["close"]

    # Volume ratio (당일 / 20일 평균)
    df["vol_ma20"] = df["volume"].rolling(20).mean()
    df["volume_ratio"] = df["volume"] / df["vol_ma20"].replace(0, float("nan"))

    # Stochastic(14,3)
    stoch = ta.momentum.StochasticOscillator(
        high=df["high"], low=df["low"], close=df["close"], window=14, smooth_window=3
    )
    df["stoch_k"] = stoch.stoch()
    df["stoch_d"] = stoch.stoch_signal()

    # 수익률 (60일 = 약 3개월, 퀀트 팩터: 중기 모멘텀 구간 포착)
    df["return_1d"] = df["close"].pct_change(1)
    df["return_5d"] = df["close"].pct_change(5)
    df["return_20d"] = df["close"].pct_change(20)
    df["return_60d"] = df["close"].pct_change(60)

    # 52주 최고가 대비 위치
    df["high_52w"] = df["high"].rolling(252).max()
    df["price_position_52w"] = df["close"] / df["high_52w"].replace(0, float("nan"))

    return df


def get_latest_indicators(df: pd.DataFrame) -> Optional[dict]:
    """지표 DataFrame의 마지막 행을 dict로 반환"""
    if df is None or df.empty:
        return None

    df_with_indicators = calculate_indicators(df)
    last = df_with_indicators.iloc[-1]

    indicator_cols = [
        "rsi",
        "macd",
        "macd_signal",
        "macd_hist",
        "bb_upper",
        "bb_mid",
        "bb_lower",
        "ema5",
        "ema20",
        "ema60",
        "atr",
        "atr_pct",
        "volume_ratio",
        "stoch_k",
        "stoch_d",
        "return_1d",
        "return_5d",
        "return_20d",
        "return_60d",
        "price_position_52w",
        "disparity_ema20",
    ]

    result = {"close": float(last["close"]), "date": str(last["date"])}
    for col in indicator_cols:
        val = last.get(col)
        result[col] = round(float(val), 4) if pd.notna(val) else None

    return result
