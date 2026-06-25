@echo off
cd /d "%~dp0"
python jalan.py %*
if errorlevel 1 pause
