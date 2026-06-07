@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Migracao status_calculado dos PTAMs
echo ============================================
echo.

rem --- Acha o Python (caminho do seu 3.14; cai pro 'py' se mudar) ---
set "PY=C:\Users\Ronicley Pinto\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if not exist "%PY%" set "PY=py"

echo --- Instalando dependencias (motor, pymongo, python-dotenv) ---
"%PY%" -m pip install --quiet --disable-pip-version-check motor pymongo python-dotenv
echo.

echo --- Rodando ---
echo (sem argumentos = aplica; use --inspect para diagnostico, --dry-run para simular)
echo.
"%PY%" migrate_ptam_status.py %*

echo.
echo ============================================
echo   Fim. Veja o resumo acima.
echo ============================================
pause
