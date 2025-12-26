$ErrorActionPreference = 'Stop'

Write-Host "[CI] Starting Flask server..."

# --- Files ---
$serverPidFile  = "server.pid"
$serverPortFile = "server.port"
$serverOut      = "server.out"
$serverErr      = "server.err"
$serverPy       = "ci_server.py"

# --- Clean old ---
Remove-Item $serverPidFile,$serverPortFile,$serverOut,$serverErr,$serverPy -ErrorAction SilentlyContinue

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

# Persist port
Set-Content -Path $serverPortFile -Value $port -Encoding ascii

# Export to subsequent GitHub Actions steps
$env:SCART_TEST_PORT = "$port"
$env:BASE_URL        = "http://127.0.0.1:$port"
if ($env:GITHUB_ENV) {
    "BASE_URL=$($env:BASE_URL)" | Out-File -FilePath $env:GITHUB_ENV -Append -Encoding utf8
    "SCART_TEST_PORT=$port"     | Out-File -FilePath $env:GITHUB_ENV -Append -Encoding utf8
}

# Safe defaults
$env:FLASK_ENV   = "production"
$env:FLASK_DEBUG = "0"

if (-not $env:SCART_DB_PATH -or $env:SCART_DB_PATH.Trim() -eq "") {
    Write-Host "[WARN] SCART_DB_PATH is empty. Server may use default DB path."
} else {
    Write-Host "[CI] SCART_DB_PATH=$env:SCART_DB_PATH"
}

# --- Write server python to file (avoid -c quoting issues) ---
@"
from app import create_app

app = create_app()
app.run(host="127.0.0.1", port=int("$port"), debug=False, use_reloader=False)
"@ | Out-File -FilePath $serverPy -Encoding utf8

# --- Start background process ---
$proc = Start-Process -FilePath python `
    -ArgumentList @($serverPy) `
    -RedirectStandardOutput $serverOut `
    -RedirectStandardError  $serverErr `
    -NoNewWindow `
    -PassThru

$proc.Id | Set-Content -Path $serverPidFile -Encoding ascii
Write-Host "[CI] Flask server started with PID $($proc.Id) on port $port"

# --- Health check ---
$healthUrl = "http://127.0.0.1:$port/health"

$maxTriesHealth = 120
$ok = $false
$lastError = $null

for ($i = 1; $i -le $maxTriesHealth; $i++) {
    try {
        Get-Process -Id $proc.Id -ErrorAction Stop | Out-Null
    } catch {
        $lastError = "Process exited before health check succeeded."
        break
    }

    try {
        $resp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
            $ok = $true
            break
        } else {
            $lastError = "HTTP Status: $($resp.StatusCode)"
        }
    } catch {
        $lastError = $_.Exception.Message
        Start-Sleep -Milliseconds 500
    }
}

if (-not $ok) {
    Write-Host "[ERROR] Health check failed: $healthUrl"
    if ($lastError) { Write-Host "[ERROR] Last error: $lastError" }

    Write-Host "----- Process alive? -----"
    try { Get-Process -Id $proc.Id | Select-Object Id, ProcessName, CPU, StartTime | Format-Table } catch { Write-Host "(dead)" }

    Write-Host "----- NetTCPConnection Listen (port $port) -----"
    try { Get-NetTCPConnection -State Listen -LocalPort $port | Format-Table } catch { Write-Host "(not listening)" }

    Write-Host "----- server.err (tail 200) -----"
    if (Test-Path $serverErr) { Get-Content $serverErr -Tail 200 } else { Write-Host "(server.err not found)" }

    Write-Host "----- server.out (tail 200) -----"
    if (Test-Path $serverOut) { Get-Content $serverOut -Tail 200 } else { Write-Host "(server.out not found)" }

    try { Stop-Process -Id $proc.Id -Force } catch {}
    exit 1
}

Write-Host "[CI] Health check OK: $healthUrl"
exit 0
