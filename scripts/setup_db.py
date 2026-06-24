"""DB 초기화 + 종목 마스터 적재"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.logging_config import setup_logging
from config.settings import settings
from core.database import init_db
from data.data_manager import initialize_stocks

if __name__ == "__main__":
    setup_logging(settings.log_level)
    print(f"DB 초기화 시작: {settings.db_path}")
    init_db()
    print("테이블 생성 완료")
    initialize_stocks()
    print(f"종목 마스터 적재 완료")
    print("setup_db.py 완료")
