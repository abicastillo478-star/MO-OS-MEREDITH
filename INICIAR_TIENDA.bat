@echo off
setlocal
cd /d "%~dp0"
title MOÑOS MEREDITH
python -m pip install -r requirements.txt
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:5000"
python app.py
