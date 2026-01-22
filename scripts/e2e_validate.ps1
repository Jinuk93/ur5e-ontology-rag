param(
  [int]$Port = 8002,
  [string]$BindHost = "127.0.0.1",
  [int]$WaitSeconds = 30,
  [switch]$ForceKillPort
)

$ErrorActionPreference = "Stop"

function Write-Info([string]$msg) { Write-Host "[INFO] $msg" }
function Write-Warn([string]$msg) { Write-Host "[WARN] $msg" }
function Write-Err([string]$msg)  { Write-Host "[ERR]  $msg" }

function Get-ListeningPids([int]$port) {
  try {
    return (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction Stop | Select-Object -ExpandProperty OwningProcess -Unique)
  } catch {
    return @()
  }
}

function Wait-HttpOk([string]$url, [int]$timeoutSeconds) {
  $deadline = (Get-Date).AddSeconds($timeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    try {
      $resp = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2
      if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
        return $true
      }
    } catch {
      Start-Sleep -Milliseconds 500
    }
  }
  return $false
}

$baseUrl = "http://$BindHost`:$Port"

# 0) 포트 정리(옵션)
$pids = Get-ListeningPids -port $Port
if ($pids.Count -gt 0) {
  if ($ForceKillPort) {
    Write-Warn "Port $Port is already in use by PID(s): $($pids -join ', '). Killing..."
    foreach ($procId in $pids) {
      try { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue } catch {}
    }
    Start-Sleep -Seconds 1
  } else {
    Write-Err "Port $Port is already in use by PID(s): $($pids -join ', '). Use -ForceKillPort or free the port."
    exit 2
  }
}

# 1) 서버 시작
Write-Info "Starting API server on $baseUrl"
$serverArgs = @(
  "scripts/run_api.py",
  "--host", $BindHost,
  "--port", $Port
)

$serverProc = Start-Process -FilePath "python" -ArgumentList $serverArgs -PassThru -WindowStyle Hidden
Write-Info "Server PID: $($serverProc.Id)"

try {
  # 2) 준비 대기
  Write-Info "Waiting for server readiness (/health)..."
  $ok = Wait-HttpOk -url "$baseUrl/health" -timeoutSeconds $WaitSeconds
  if (-not $ok) {
    Write-Err "Server did not become ready within ${WaitSeconds}s."
    exit 3
  }

  # 3) 검증 실행
  Write-Info "Running acceptance validation (scripts/validate_api.py)..."
  python scripts/validate_api.py --base-url $baseUrl --wait-seconds 0
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0) {
    Write-Err "Validation failed (exit code: $exitCode)"
    exit $exitCode
  }

  Write-Info "Validation passed"
  exit 0
}
finally {
  # 4) 서버 종료
  Write-Info "Stopping server PID $($serverProc.Id)"
  try { Stop-Process -Id $serverProc.Id -Force -ErrorAction SilentlyContinue } catch {}

  # 5) 포트 해제 확인(최선)
  Start-Sleep -Milliseconds 800
  $remaining = Get-ListeningPids -port $Port
  if ($remaining.Count -gt 0) {
    Write-Warn "Port $Port still has listener PID(s): $($remaining -join ', ')"
  } else {
    Write-Info "Port $Port is free"
  }
}
