@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m harness.web
) else (
  python -m harness.web
)
if errorlevel 1 pause
