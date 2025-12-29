@echo off
REM Opens two PowerShell windows: one runs server.py, the other runs client.py
cd /d "%~dp0"

echo ========================================
echo Starting Healthy Mario Bros Server
echo ========================================
echo.

REM Start server in its own PowerShell window (keep window open)
REM Activate conda environment mp_env before running
start "Server - Healthy Mario Bros" powershell -NoExit -ExecutionPolicy Bypass -Command "conda activate mp_env; python -u server.py"

REM Give server time to fully initialize
REM Server needs to: initialize pygame, load assets, bind socket, start accept thread
echo Waiting for server to initialize (5 seconds)...
echo Please wait for "Server listening on..." message in the server window.
timeout /t 5 >nul

echo.
echo ========================================
echo Starting Client
echo ========================================
echo.

REM Start client in its own PowerShell window
REM Activate conda environment mp_env before running
REM Client will prompt for role input - user needs to type 'P' or 'O'
start "Client - Healthy Mario Bros" powershell -NoExit -ExecutionPolicy Bypass -Command "conda activate mp_env; python -u client.py"

echo.
echo ========================================
echo Both windows are now open!
echo ========================================
echo.
echo IMPORTANT: Check the SERVER window first!
echo   It should show:
echo     "Server listening on 0.0.0.0:5000"
echo     "Waiting for players to connect..."
echo.
echo In the CLIENT window, type: P
echo (P for Player, O for Observer)
echo.
echo ========================================
echo TROUBLESHOOTING:
echo ========================================
echo If connection fails, try running:
echo   python test_connection.py
echo.
echo This will test if the server is responding.
echo.
pause

exit /b 0
