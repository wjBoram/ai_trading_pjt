@echo off
chcp 65001 > nul
echo ====================================
echo 국내주식 AI 자동매매 시스템 시작
echo ====================================

REM DB 초기화 (없으면)
if not exist "data_store\trading.db" (
    echo DB 초기화 중...
    python scripts\setup_db.py
    echo OHLCV 데이터 수집 중 (최초 1회)...
    python scripts\backfill_data.py
)

REM FastAPI 백엔드
echo FastAPI 백엔드 시작...
start "FastAPI Backend" cmd /k "python main.py"

timeout /t 3 /nobreak > nul

REM Streamlit 대시보드
echo Streamlit 대시보드 시작...
start "Streamlit Dashboard" cmd /k "streamlit run streamlit_app.py --server.port 8501"

echo.
echo 서비스 시작 완료
echo  - FastAPI  : http://localhost:8000/docs
echo  - Dashboard: http://localhost:8501
echo.
pause
