$ErrorActionPreference = 'Stop'
$maxTries = 20
$found = $false
for ($try = 0; $try -lt $maxTries; $try++) {
    $port = Get-Random -Minimum 20000 -Maximum 40000
    $inUse = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if (-not $inUse) {
        $found = $true
        break
    }
}
if (-not $found) {
    Write-Host "[ERROR] Could not find free port after $maxTries tries"
    exit 1
}
Write-Host "[INFO] Selected free port: $port"
$env:SCART_TEST_PORT = $port
$env:BASE_URL = "http://127.0.0.1:$port"
if ($env:GITHUB_ENV) {
    Write-Output "BASE_URL=$($env:BASE_URL)" | Out-File -FilePath $env:GITHUB_ENV -Append
    Write-Output "SCART_TEST_PORT=$port" | Out-File -FilePath $env:GITHUB_ENV -Append
}
Write-Output $port | Out-File -FilePath server.port -Encoding ascii
$serverOut = "server.out"
$serverErr = "server.err"
$serverPid = "server.pid"
$env:FLASK_APP = "app.py"
$env:FLASK_ENV = "production"
$env:FLASK_DEBUG = "0"
$proc = Start-Process -FilePath python -ArgumentList "-m", "flask", "run", "--host", "127.0.0.1", "--port", "$port" -RedirectStandardOutput $serverOut -RedirectStandardError $serverErr -PassThru
$proc.Id | Out-File -FilePath $serverPid -Encoding ascii
Write-Host "[INFO] Flask server started with PID $($proc.Id) on port $port"
$maxTriesHealth = 30
 $success = $false
 $lastError = $null
for ($i = 0; $i -lt $maxTriesHealth; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$port/health" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
            Write-Host "[INFO] Health check succeeded (port $port, try $i)"
            $success = $true
            break
        }
    } catch {
        $lastError = $_.Exception.Message
        Start-Sleep -Seconds 2
    }
}
if (-not $success) {
    Write-Host "[ERROR] Health check failed after $maxTriesHealth tries (port $port)"
    $diagDir = "artifacts/ci_diag"
    if (-not (Test-Path $diagDir)) { New-Item -ItemType Directory -Path $diagDir -Force | Out-Null }
    $diagFile = "$diagDir/start_server_failed.txt"
    $lines = @()
    $lines += "==== CI DIAG: Health check failed ===="
    $lines += "Port: $port"
    $lines += "BASE_URL: $env:BASE_URL"
    $procAlive = $false
    try {
        $procTest = Get-Process -Id $proc.Id -ErrorAction Stop
        $procAlive = $true
    } catch {}
    $procAliveLabel = "no"
    if ($procAlive) { $procAliveLabel = "yes" }
    $lines += "Process alive: $procAliveLabel"
    $lines += "--- NetTCPConnection (port $port) ---"
    try {
        $lines += (Get-NetTCPConnection -LocalPort $port -State Listen | Out-String)
    } catch {
        $lines += "Get-NetTCPConnection failed: $($_.Exception.Message)"
    }
    $lines += "--- Process Info (PID $($proc.Id)) ---"
    try { $lines += (Get-Process -Id $proc.Id | Format-List * | Out-String) } catch { $lines += "Process info not available" }
    $envKeys = Get-ChildItem Env: | Select-Object -ExpandProperty Name | Sort-Object
    $lines += "--- Env Keys ---"
    $lines += ("Env key count: " + $envKeys.Count)
    $lines += $envKeys
    if (Test-Path $serverOut) {
        $lines += "--- server.out (last 200 lines) ---"
        $lines += (Get-Content $serverOut -Tail 200 | Out-String)
    }
    if (Test-Path $serverErr) {
        $lines += "--- server.err (last 200 lines) ---"
        $lines += (Get-Content $serverErr -Tail 200 | Out-String)
    }
    $lines += "--- Last health check error ---"
    if ($null -eq $lastError -or $lastError -eq "") { $lines += "(none)" } else { $lines += $lastError }
    $lines | Out-File -FilePath $diagFile -Encoding utf8
    if (Test-Path $serverPid) {
        $serverProcessId = Get-Content $serverPid
        try { Stop-Process -Id $serverProcessId -Force } catch {}
    }
    exit 1
}
