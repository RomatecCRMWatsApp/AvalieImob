@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PY=C:\Users\Ronicley Pinto\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if not exist "%PY%" set "PY=py"
"%PY%" diag_pdfs.py
echo.
pause
