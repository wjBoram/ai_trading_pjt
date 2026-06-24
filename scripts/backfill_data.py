"""2년치 OHLCV 백필 (최초 1회 실행)"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.logging_config import setup_logging
from config.settings import settings
from core.database import init_db
from data.data_manager import backfill_ohlcv, initialize_stocks

if __name__ == "__main__":
    setup_logging(settings.log_level)
    init_db()
    initialize_stocks()
    print("OHLCV 백필 시작 (약 2~5분 소요)...")
    backfill_ohlcv(days=730)
    print("백필 완료")
