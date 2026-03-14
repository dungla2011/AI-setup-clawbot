@echo off
REM Script để chạy cả API + Web server cùng lúc (Windows)

echo.
echo ========================================
echo Bot MVP - Full Setup (Windows)
echo ========================================
echo.

REM Check venv
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate venv
echo Activating venv...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -q -r requirements.txt

REM Check .env file
if not exist ".env" (
    echo Creating .env from template...
    copy .env.example .env
    echo.
    echo ERROR: Configure ANTHROPIC_API_KEY in .env file!
    echo Open .env and replace sk-ant-your-api-key-here with real API key
    pause
)

REM Check API key
findstr /M "sk-ant-your-api-key-here" .env >nul
if not errorlevel 1 (
    echo ERROR: ANTHROPIC_API_KEY not configured in .env!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo Run 2 servers in different terminals:
echo.
echo Terminal 1 (API Server):
echo    python api.py
echo.
echo Terminal 2 (Web Server):
echo    python web_server.py
echo.
echo Then open: http://localhost:8080/index.html
echo ========================================
echo.
pause
