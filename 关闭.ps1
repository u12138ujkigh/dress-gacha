# 关闭装扮抽卡 WebUI
$ErrorActionPreference = 'SilentlyContinue'
$APP  = Split-Path -Parent $MyInvocation.MyCommand.Path
$DATA = Join-Path $APP 'data'
$PIDF = Join-Path $DATA 'server.pid'

function Get-Listener {
    (Get-NetTCPConnection -LocalPort 8770 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1).OwningProcess
}

$killed = $false

# Prefer the pid this app recorded; it is the only process we are entitled to
# kill. Fall back to the port owner when the file is gone.
if (Test-Path $PIDF) {
    $pidText = (Get-Content $PIDF -Raw).Trim()
    if ($pidText -match '^\d+$') {
        $proc = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -like 'python*') {
            Stop-Process -Id ([int]$pidText) -Force
            $killed = $true
        }
    }
    Remove-Item $PIDF -Force -ErrorAction SilentlyContinue
}

if (-not $killed) {
    $p = Get-Listener
    if ($p) {
        $proc = Get-Process -Id $p -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -like 'python*') {
            Stop-Process -Id $p -Force
            $killed = $true
        }
    }
}

if ($killed) { Write-Host '装扮抽卡已关闭' -ForegroundColor Green }
else { Write-Host '没有在运行' -ForegroundColor DarkGray }
Start-Sleep -Seconds 2
