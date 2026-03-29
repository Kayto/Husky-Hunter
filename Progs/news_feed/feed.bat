@echo off
REM feed.bat — BBC News Feed for Husky Hunter
REM Double-click to start. Press Ctrl+C to stop.
REM Usage: feed.bat [COMx] [interval]
REM   e.g. feed.bat COM3 10

set PORT=%1
if "%PORT%"=="" set PORT=COM8

set INTERVAL=%2
if "%INTERVAL%"=="" set INTERVAL=15

echo =======================================
echo  BBC News Feed - Husky Hunter
echo =======================================
echo.
echo  Port:     %PORT%
echo  Interval: %INTERVAL%s per headline
echo.
echo  Press Ctrl+C to stop.
echo =======================================
echo.

python "%~dp0feed.py" -p %PORT% -i %INTERVAL%

echo.
echo Feed stopped.
echo.
pause
