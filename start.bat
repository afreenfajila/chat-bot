@echo off
echo.
echo  VoiceChat - Multilingual AI Voice Assistant
echo  ============================================

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found. Install it from https://python.org and try again.
    pause
    exit /b 1
)

:: Check Ollama is available
ollama --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Ollama not found. Install it from https://ollama.com and run:
    echo    ollama pull aisingapore/Gemma-SEA-LION-v4-4B-VL
    pause
    exit /b 1
)

echo.
echo  Installing dependencies...
pip install -r requirements.txt --quiet

echo.
echo  Starting server at http://localhost:5000
echo  Press Ctrl+C to stop.
echo.
python app.py
