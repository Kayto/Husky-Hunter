@echo off
REM =============================================
REM  Husky HCOM Launcher
REM =============================================
REM  Usage:  LaunchHCOM.bat           (normal launch)
REM          LaunchHCOM.bat --setup   (reconfigure)
REM
REM  By Kayto 28/03/2026
REM  Licensed under the MIT License.
REM  See LICENSE file for details.
REM =============================================
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0LaunchHCOM.ps1" %*


endlocal
