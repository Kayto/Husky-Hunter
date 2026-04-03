@echo off
REM =============================================
REM  Husky Hunter Dev Sync (From Hunter)
REM =============================================
REM  Downloads files from the Hunter into HSYNC\
REM  and updates the sync manifest.
REM
REM  By Kayto 02/04/2026
REM  Licensed under the MIT License.
REM  See LICENSE file for details.
REM =============================================

cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0SyncFromHunter.ps1"
