@echo off
REM Opens two PowerShell windows: one runs server.py, the other runs client.py and sends "p" as input.
cd /d "%~dp0"

REM Start server in its own PowerShell window (keep window open)
start "Server" powershell -NoExit -ExecutionPolicy Bypass -Command "python -u server.py"

REM Give server a short moment to start, then launch client and pipe 'p' into it
timeout /t 1 >nul
start "Client" powershell -NoExit -ExecutionPolicy Bypass -Command "echo p | python -u client.py"

exit /b 0
