$serverPid = "server.pid"
$port = 5000
if (Test-Path server.port) {
    $port = Get-Content server.port | Select-Object -First 1
} else {
    Write-Host "[WARN] server.port not found, using default port 5000"
}

# Diagnostic: Save port LISTEN status before and after stop attempts
$diagDir = "artifacts/ci_diag"
if (-not (Test-Path $diagDir)) { New-Item -ItemType Directory -Path $diagDir -Force | Out-Null }
$diagFile = "$diagDir/stop_server.txt"
$diagLines = @()
$diagLines += "==== CI DIAG: Stop server ===="
$diagLines += "Port: $port"
$diagLines += "--- NetTCPConnection BEFORE stop (port $port) ---"

try {
    $diagLines += (Get-NetTCPConnection -LocalPort $port -State Listen | Out-String)
} catch {
    $diagLines += "Get-NetTCPConnection failed: $($_.Exception.Message)"
}

$stoppedPids = @()
if (Test-Path $serverPid) {
    $pid = Get-Content $serverPid
    try {
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Write-Host "[INFO] Flask server stopped (PID $pid)"
        $stoppedPids += $pid
    } catch {
        Write-Host "[WARN] Could not stop server (PID $pid)"
    }
} else {
    Write-Host "[WARN] server.pid not found, nothing to stop"
}
$conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($conns) {
    $pids = $conns | Select-Object -ExpandProperty OwningProcess | Select-Object -Unique
    foreach ($portPid in $pids) {
        if ($stoppedPids -notcontains $portPid) {
            try {
                Stop-Process -Id $portPid -Force -ErrorAction SilentlyContinue
                Write-Host "[INFO] Port $port process stopped (PID $portPid)"
            } catch {
                Write-Host "[WARN] Could not stop port $port process (PID $portPid)"
            }
        }
    }
}
$stillListening = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($stillListening) {
    Write-Host "[WARN] Port $port still listening after stop attempts"
}
$diagLines += "--- NetTCPConnection AFTER stop (port $port) ---"

try {
    $diagLines += (Get-NetTCPConnection -LocalPort $port -State Listen | Out-String)
} catch {
    $diagLines += "Get-NetTCPConnection failed: $($_.Exception.Message)"
}
$diagLines | Out-File -FilePath $diagFile -Encoding utf8
