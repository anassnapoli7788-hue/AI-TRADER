@echo off
title Six-Agent AI Trading Desk - Launcher
echo ================================================
echo   SIX-AGENT AI TRADING DESK
echo   Nova / Axiom / Pulse / Onyx / Orion / Veto
echo   Website:  http://127.0.0.1:8020
echo ================================================
echo.
echo Starting the backend (new window will open)...
if exist "%~dp0local-secrets.bat" call "%~dp0local-secrets.bat"
start "Trading Desk Backend" powershell -NoExit -ExecutionPolicy Bypass -Command "cd 'C:\Users\Anas\Desktop\ai trader\solana-ai-desk\backend'; py -3.12 run.py --port 8020"
echo.
echo Waiting for the backend to come up...
timeout /t 8 /nobreak >nul
echo Opening the website in your browser...
start http://127.0.0.1:8020
echo.
echo DONE. The website is served by the backend window.
echo Keep the backend window OPEN while using the desk.
echo Close it (or press Ctrl+C there) to stop the desk.
echo.
pause
