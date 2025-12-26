Write-Host "[CI] Stopping Flask server..."

$serverPidFile  = "server.pid"
$serverPortFile = "server.port"
$diagDir  = "artifacts/ci_diag"
$diagFile = Join-Path $diagDir "stop_server.txt"

if (-not (Test-Path $diagDir)) {
    New-Item -ItemType Directory -Force -Path $diagDir | Out-Null
}

# --- read port (optional) ---
$port = $null
if (Test-Path $serverPortFile) {
    $portRaw = Get-Content $serverPortFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($portRaw -and ($portRaw -as [int])) { $port = [int]$portRaw }
}

# --- read pid (optional) ---
$serverProcessId = $null
if (Test-Path $serverPidFile) {
    $pidRaw = Get-Content $serverPidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pidRaw -and ($pidRaw -as [int])) { $serverProcessId = [int]$pidRaw }
}

# --- diagnostics helper (never throws) ---
function Get-ListenConnsText([int]$p) {
    try {
        $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
        if ($null -eq $conns) { return "(no listening connections)" }
        return ($conns | Format-Table -AutoSize | Out-String)
    } catch {
        return "Get-NetTCPConnection failed: $($_.Exception.Message)"
    }
}

$diagLines = @()
$diagLines += "==== CI DIAG: Stop server (best effort) ===="
$diagLines += "Time: $(Get-Date -Format o)"
$diagLines += "server.pid exists: $(Test-Path $serverPidFile)"
$diagLines += "server.port exists: $(Test-Path $serverPortFile)"
$diagLines += "PID (from file): $serverProcessId"
$diagLines += "Port (from file): $port"
$diagLines += ""

if ($port) {
    $diagLines += "--- NetTCPConnection BEFORE stop (port $port) ---"
    $diagLines += (Get-ListenConnsText $port)
    $diagLines += ""
}

# --- stop by PID (best effort) ---
if ($serverProcessId) {
    Write-Host "[CI] Trying to stop PID=$serverProcessId"
    try {
        Stop-Process -Id $serverProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "[CI] Stop-Process issued for PID=$serverProcessId"
    } catch {
        Write-Host "[CI] PID already stopped or not found"
    }
} else {
    Write-Host "[CI] server.pid not found or invalid; skipping PID stop"
}

# --- optional: if port still listening, kill owning processes (best effort) ---
if ($port) {
    try {
        $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if ($conns) {
            $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($owningPid in $pids) {
                if ($serverProcessId -and ($owningPid -eq $serverProcessId)) { continue }
                Write-Host "[CI] Trying to stop owning process PID=$owningPid for port $port"
                Stop-Process -Id $owningPid -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {
        # ignore
    }

    $diagLines += "--- NetTCPConnection AFTER stop (port $port) ---"
    $diagLines += (Get-ListenConnsText $port)
    $diagLines += ""
}

# --- write diag (never fail) ---
try {
    $diagLines | Out-File -FilePath $diagFile -Encoding utf8
    Write-Host "[CI] Wrote diagnostics: $diagFile"
} catch {
    Write-Host "[CI] Failed to write diagnostics (ignored): $($_.Exception.Message)"
}

Write-Host "[CI] Stop server finished (best effort)"
exit 0
