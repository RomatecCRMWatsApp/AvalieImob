param(
  [switch]$Deploy,
  [string]$Service = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")

Write-Host "[auto] Repo root: $repoRoot"

function Require-Command {
  param([string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command '$Name' not found in PATH."
  }
}

Require-Command "npm"
Require-Command "python"

Write-Host "[auto] Step 1/3 - Frontend build"
Push-Location (Join-Path $repoRoot "frontend")
try {
  if (-not (Test-Path "node_modules")) {
    Write-Host "[auto] node_modules not found; running npm ci"
    npm ci
  }
  npm run build
} finally {
  Pop-Location
}

Write-Host "[auto] Step 2/3 - Backend syntax check"
Push-Location $repoRoot
try {
  python -m compileall backend
} finally {
  Pop-Location
}

if ($Deploy) {
  Write-Host "[auto] Step 3/3 - Railway deploy"
  Require-Command "railway"

  Push-Location $repoRoot
  try {
    if ([string]::IsNullOrWhiteSpace($Service)) {
      railway up
    } else {
      railway up --service $Service
    }
  } finally {
    Pop-Location
  }

  Write-Host "[auto] Done: build validated and deploy triggered."
} else {
  Write-Host "[auto] Step 3/3 - Deploy skipped"
  Write-Host "[auto] Done: build validated."
  Write-Host "[auto] To deploy automatically: npm run auto:deploy"
}
