@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 -m pip install -r requirements.txt
if errorlevel 1 goto failed
py -3 bot.py
goto end
:use_python
python -m pip install -r requirements.txt
if errorlevel 1 goto failed
python bot.py
goto end
:failed
echo Install Python 3.9+ from python.org and enable Add Python to PATH.
:end
pause
