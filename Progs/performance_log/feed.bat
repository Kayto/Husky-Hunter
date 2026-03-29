@echo off
REM feed.bat — PC Performance Logger Feed for Husky Hunter
REM Double-click to start. Press Ctrl+C to stop.
REM Usage: feed.bat [COMx] [interval]
REM   e.g. feed.bat COM3 2.0

set PORT=%1
if "%PORT%"=="" set PORT=COM8

set INTERVAL=%2
if "%INTERVAL%"=="" set INTERVAL=1.0

echo =======================================
echo  PC Performance Logger - Husky Hunter
echo =======================================
echo.
echo  Port:     %PORT%
echo  Interval: %INTERVAL%s
echo.
echo  Press Ctrl+C to stop.
echo ===================================
echo.

python "%~dp0feed.py" -p %PORT% -i %INTERVAL%

echo.
echo Feed stopped.
echo.
pause
