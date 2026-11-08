@echo off
rem Windows Task Scheduler launcher: update MOLIT truck registration stats in MySQL
rem (keep this file ASCII-only; cmd.exe reads it before the code page is changed)
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0.."
".venv\Scripts\python.exe" scripts\update_registration_db.py
exit /b %ERRORLEVEL%
