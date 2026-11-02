@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto usepython
py -3 "%~dp0iachara_to_charash.py"
goto finished
:usepython
python "%~dp0iachara_to_charash.py"
:finished
if errorlevel 1 pause
