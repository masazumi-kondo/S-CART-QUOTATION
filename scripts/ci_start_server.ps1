$ErrorActionPreference = 'Stop'

Write-Host "[CI] Starting Flask server..."

# --- Files ---
$serverPidFile  = "server.pid"
$serverPortFile = "server.port"
$serverOut      = "server.out"
$serverErr      = "server.err"

# --- Clean old ---
Remove-Item $serverPidFile,$serverPortFile,$serverOut,$serverErr -ErrorAction SilentlyContinue

# --- Pick free port ---
function Get-FreePort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $p = $listener.LocalEndpoint.Port
    $listener.Stop()
    return $p
}
$port = Get-FreePort
Write-Host "[CI] Selected free port: $port"

# Persist port (other scripts can read it)
Set-Content -Path $serverPortFile -Value $port -Encoding ascii

# --- Build python inline server ---
# IMPORTANT: use_reloader=False (avoid double process)
$code = @"
from app import create_app
app = create_app()
app.run(host="127.0.0.1", port=int($port), debug=False, use_reloader=False)
"@

# --- Start background process (with env inheritance) ---
# Use Start-Process so stdout/err redirection is stable on Windows runner.
$env:SCART_TEST_PORT = "$port"
$env:BASE_URL        = "http://127.0.0.1:$port"

# Export to subsequent GitHub Actions steps
if ($env:GITHUB_ENV) {
    "BASE_URL=$($env:BASE_URL)"      | Out-File -FilePath $env:GITHUB_ENV -Append -Encoding utf8
    "SCART_TEST_PORT=$port"          | Out-File -FilePath $env:GITHUB_ENV -Append -Encoding utf8
}

# Optional but recommended: these are safe defaults for CI
$env:FLASK_ENV   = "production"
$env:FLASK_DEBUG = "0"

# Ensure DB path is actually visible to the python process
# (YAML step must set SCART_DB_PATH; this line just confirms it's present)
if (-not $env:SCART_DB_PATH -or $env:SCART_DB_PATH.Trim() -eq "") {
    Write-Host "[WARN] SCART_DB_PATH is empty. Server may use default DB path."
} else {
    Write-Host "[CI] SCART_DB_PATH=$env:SCART_DB_PATH"
}

$proc = Start-Process -FilePath python `
    -ArgumentList @("-c", $code) `
    -RedirectStandardOutput $serverOut `
    -RedirectStandardError  $serverErr `
    -NoNewWindow `
    -PassThru

$proc.Id | Set-Content -Path $serverPidFile -Encoding ascii
Write-Host "[CI] Flask server started with PID $($proc.Id) on port $port"

# --- Health check ---
$healthUrl = "http://127.0.0.1:$port/health"
$ok = $false
$lastError = $null

for ($i = 1; $i -le 60; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
            $ok = $true
            break
        }
    } catch {
        $lastError = $_.Exception.Message
        Start-Sleep -Milliseconds 500
    }
}

if (-not $ok) {
    Write-Host "[ERROR] Health check failed: $healthUrl"
    if ($lastError) { Write-Host "[ERROR] Last error: $lastError" }

    Write-Host "----- server.err (tail 200) -----"
    if (Test-Path $serverErr) { Get-Content $serverErr -Tail 200 }

    Write-Host "----- server.out (tail 200) -----"
    if (Test-Path $serverOut) { Get-Content $serverOut -Tail 200 }

    Write-Host "----- NetTCPConnection Listen (port $port) -----"
    try { Get-NetTCPConnection -State Listen -LocalPort $port | Format-Table } catch {}

    # cleanup
    try { Stop-Process -Id $proc.Id -Force } catch {}
    exit 1
}

Write-Host "[CI] Health check OK: $healthUrl"
exit 0
