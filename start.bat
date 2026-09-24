@echo off
chcp 65001 > nul
title Pocket Trading Signals & AI Terminal
echo =======================================================
echo    AI TRADING TERMINAL ^& TELEGRAM BOT SIGNALS (90%+)
echo =======================================================
echo.
echo [1] Проверка зависимостей...
python -m pip install -r requirements.txt
echo.
echo [2] Запуск сервера и терминала...
echo.
echo Откройте в браузере: http://localhost:8000
echo Для выхода нажмите Ctrl+C
echo =======================================================
echo.
python run.py
pause
