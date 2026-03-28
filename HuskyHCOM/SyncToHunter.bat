@echo off
REM =============================================
REM  Husky Hunter Dev Sync
REM =============================================
REM  Compares HSYNC\ against last sync and
REM  pushes changes to Hunter via CMDHCOM.
REM
REM  By Kayto 28/03/2026
REM  Licensed under the MIT License.
REM  See LICENSE file for details.
REM =============================================

cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0SyncToHunter.ps1"
