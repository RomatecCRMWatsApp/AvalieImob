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

echo --- Arquivos alterados ---
git status --short
echo.

git add -A
git commit -m "feat(ptam): visualizador PDF inline no card + versao v1.0.N incremental com data/hora"

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
echo   DEPLOY ENVIADO COM SUCESSO!
echo   O CI (GitHub - Railway) vai buildar e publicar.
echo   A versao vai subir para v1.0.335 automaticamente.
echo ============================================
echo.
pause
