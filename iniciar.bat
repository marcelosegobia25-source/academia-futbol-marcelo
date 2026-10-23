@echo off
cd /d "%~dp0"
echo Iniciando Academia de Futbol...
start http://127.0.0.1:5000
.venv\Scripts\python.exe desktop.py
pause
