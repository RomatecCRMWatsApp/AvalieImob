<#
  push-deploy.ps1  —  Push guiado + rotacao do remote (Romatec AvalieImob)
  ------------------------------------------------------------------------
  - Limpa o token embutido na URL do remote (seguranca)
  - Pede um Personal Access Token NOVO de forma segura (nao fica no historico)
  - Faz push para 'main' (dispara CI -> Railway deploy hook)
  - Nao grava o token em texto puro no .git/config

  USO:
    powershell -ExecutionPolicy Bypass -File .\scripts\push-deploy.ps1

  Pre-requisito: gerar um PAT novo em
    GitHub -> Settings -> Developer settings -> Personal access tokens
    Escopo minimo: 'repo' (classic) ou 'Contents: Read and write' (fine-grained)
#>

param(
  [string]$Branch = "main",
  [string]$RepoUrl = "https://github.com/RomatecCRMWatsApp/AvalieImob.git"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Step($msg) { Write-Host "`n[deploy] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[ ok ] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[warn] $msg" -ForegroundColor Yellow }

# 1) Garante que estamos na raiz do repo -------------------------------------
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $repoRoot
Write-Step "Repo root: $repoRoot"

if (-not (Test-Path ".git")) { throw "Nao parece ser um repositorio git: $repoRoot" }

# 2) Mostra o estado atual ----------------------------------------------------
Write-Step "Branch atual e commits pendentes de push:"
git rev-parse --abbrev-ref HEAD
git log origin/$Branch..HEAD --oneline 2>$null
if ($LASTEXITCODE -ne 0) { Write-Warn "Nao foi possivel comparar com origin/$Branch (sera resolvido no fetch)." }

# 3) Limpa o token embutido no remote (seguranca) -----------------------------
$current = (git remote get-url origin) 2>$null
if ($current -match "@github\.com" -and $current -match "https://[^@]+@") {
  Write-Warn "Remote 'origin' contem credencial embutida na URL. Limpando..."
  git remote set-url origin $RepoUrl
  Write-Ok "Remote 'origin' agora aponta para: $RepoUrl (sem token)"
} else {
  Write-Ok "Remote 'origin' ja esta limpo: $current"
}

# 4) Pede o PAT novo de forma segura ------------------------------------------
Write-Step "Cole o Personal Access Token NOVO (a digitacao fica oculta)."
Write-Host "       Gere em: GitHub > Settings > Developer settings > Tokens" -ForegroundColor DarkGray
$secure = Read-Host -AsSecureString "PAT"
$bstr   = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$token  = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
if ([string]::IsNullOrWhiteSpace($token)) { throw "Token vazio. Abortado." }

# 5) Push usando o token apenas em memoria (URL temporaria) -------------------
$pushUrl = $RepoUrl -replace "^https://", "https://x-access-token:$token@"
Write-Step "Fazendo fetch e push para '$Branch'..."
$env:GIT_TERMINAL_PROMPT = "0"
try {
  git fetch $pushUrl $Branch 2>$null
  git push $pushUrl "HEAD:$Branch"
  if ($LASTEXITCODE -ne 0) { throw "git push retornou codigo $LASTEXITCODE" }
  Write-Ok "Push concluido. CI iniciado -> ao passar, Railway faz o deploy automatico."
}
finally {
  # Apaga o token da memoria
  $token   = $null
  $pushUrl = $null
  [System.GC]::Collect()
}

# 6) Oferece gravar o token no Git Credential Manager (sem texto puro) --------
Write-Step "Proximos pushes: rode apenas 'git push origin $Branch'."
Write-Host "       Na primeira vez o Windows pedira login do GitHub e guardara no" -ForegroundColor DarkGray
Write-Host "       Gerenciador de Credenciais (seguro). Nao reedite a URL com o token." -ForegroundColor DarkGray

Write-Ok "Fluxo finalizado."
Write-Host "`nAcompanhe o deploy em: https://github.com/RomatecCRMWatsApp/AvalieImob/actions" -ForegroundColor Cyan
