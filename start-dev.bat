@echo off
REM AI-BOS one-click dev launcher (double-click me)
REM Runs start-dev.ps1 bypassing execution policy.
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0start-dev.ps1"
