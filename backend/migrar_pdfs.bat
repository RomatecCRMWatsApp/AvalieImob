@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Migracao PDF -^> paginas PNG 300 DPI
echo ============================================
echo.

rem --- Acha o Python (caminho do seu 3.14; cai pro 'py' se mudar) ---
set "PY=C:\Users\Ronicley Pinto\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if not exist "%PY%" set "PY=py"

echo --- Instalando dependencias (PyMuPDF, Pillow, pymongo, python-dotenv) ---
"%PY%" -m pip install --quiet --disable-pip-version-check PyMuPDF Pillow pymongo python-dotenv
echo.

echo --- Rodando a migracao ---
echo (sem argumentos = DRY-RUN, nao grava nada; passe --apply para efetivar)
echo.
"%PY%" migrate_pdfs_to_pages.py %*

echo.
echo ============================================
echo   Fim. Veja o resumo acima.
echo ============================================
pause
