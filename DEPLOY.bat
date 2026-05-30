@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   DEPLOY AvalieImob - commit + push
echo ============================================
echo.
echo Pasta: %cd%
echo.

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Esta pasta nao e um repositorio git.
  echo.
  pause
  exit /b 1
)

echo --- Atualizando numero de build ---
set "BUILDNUM="
for /f "delims=" %%i in ('git rev-list --count HEAD 2^>nul') do set "BUILDNUM=%%i"
if not defined BUILDNUM set "BUILDNUM=0"
set /a BUILDNUM=BUILDNUM+1
> "frontend\build-number.txt" echo %BUILDNUM%
echo Esta versao sera: v1.0.%BUILDNUM%
echo.

echo --- Arquivos alterados ---
git status --short
echo.

git add -A
git commit -m "deploy AvalieImob v1.0.%BUILDNUM%"

if errorlevel 1 (
  echo.
  echo [AVISO] Nada para commitar OU o commit falhou. Veja a mensagem acima.
  echo.
  pause
  exit /b 1
)

echo.
echo --- Enviando para o repositorio remoto (push) ---
git push

if errorlevel 1 (
  echo.
  echo [ERRO] O push falhou. Copie a mensagem acima e me mande.
  echo.
  pause
  exit /b 1
)

echo.
echo ============================================
echo   DEPLOY ENVIADO COM SUCESSO!  v1.0.%BUILDNUM%
echo   O CI (GitHub - Railway) vai buildar e publicar.
echo ============================================
echo.
pause
