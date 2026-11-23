# 启动装扮抽卡 WebUI
$ErrorActionPreference = 'SilentlyContinue'
$APP   = Split-Path -Parent $MyInvocation.MyCommand.Path
$DATA  = Join-Path $APP 'data'
$LOG   = Join-Path $DATA 'server.log'
$PIDF  = Join-Path $DATA 'server.pid'
$LTRACE= Join-Path $DATA 'launch.log'
$URL   = 'http://127.0.0.1:8770'

function Trace([string]$m) {
    try { Add-Content -Path $LTRACE -Value ("{0} {1}" -f (Get-Date -Format 'HH:mm:ss'), $m) -Encoding utf8 } catch {}
}
Trace '==== launch begin ===='

# ---- 环境变量大小写去重 ----
# Windows 系统代理（Clash 等）常同时注入 http_proxy/HTTP_PROXY 这类大小写不同的键。
# PowerShell 7 的 Start-Process 在构造子进程环境字典时会因大小写冲突抛
# ArgumentException（"字典中已添加关键字"），导致 server 与窗口都起不来 —— 这是
# "打不开"的根因。这里按大小写不敏感去重：保留首次出现的键，删除后出现的重复键，
# 值不变，因此代理仍然有效，只是不再有大小写重复的键。
try {
    $seen = @{}
    $dups = @()
    foreach ($k in @([System.Environment]::GetEnvironmentVariables('Process').Keys)) {
        $lo = $k.ToLowerInvariant()
        if ($seen.ContainsKey($lo)) { $dups += $k } else { $seen[$lo] = $k }
    }
    foreach ($k in $dups) {
        try { [System.Environment]::SetEnvironmentVariable($k, $null, 'Process') } catch {}
    }
    if ($dups.Count) { Trace ("env dedup removed: " + ($dups -join ', ')) }
} catch {}

if (-not (Test-Path $DATA)) { New-Item -ItemType Directory -Path $DATA | Out-Null }

# 原生窗口启动器：直接用无控制台的 pythonw。
# 注意：不要用 "& pythonw -c 'import webview'" 探测再读 $LASTEXITCODE —— 在
# 隐藏窗口/无控制台的 PowerShell 里 $LASTEXITCODE 有时是空的，会把可用的
# pythonw 误判成不可用，导致窗口起不来（打不开）。venv 存在就直接用。
$DESKTOP = Join-Path $APP 'desktop_window.py'
$VENV_PYW = 'C:\Users\ximu\.workbuddy\binaries\python\envs\default\Scripts\pythonw.exe'
$WEBVIEW_PY = $null
$WEBVIEW_IS_PYLAUNCHER = $false
if ((Test-Path $DESKTOP) -and (Test-Path $VENV_PYW)) {
    $WEBVIEW_PY = $VENV_PYW
} elseif (Test-Path $DESKTOP) {
    $WEBVIEW_PY = 'pyw'
    $WEBVIEW_IS_PYLAUNCHER = $true
}
Trace "desktop=$(Test-Path $DESKTOP) webview_py=$WEBVIEW_PY"

# 回退：Edge --app 模式，仅当没有原生窗口启动器时用
$EDGE = (Get-Command msedge.exe -ErrorAction SilentlyContinue).Source
if (-not $EDGE) {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
    )
    $EDGE = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

function Open-AppWindow {
    param([string]$Target)
    if ($WEBVIEW_PY) {
        if ($WEBVIEW_IS_PYLAUNCHER) {
            Start-Process -FilePath $WEBVIEW_PY -ArgumentList @('-3.13', "`"$DESKTOP`"") `
                -WorkingDirectory $APP -WindowStyle Hidden
        } else {
            Start-Process -FilePath $WEBVIEW_PY -ArgumentList @("`"$DESKTOP`"") `
                -WorkingDirectory $APP -WindowStyle Hidden
        }
        Trace 'opened native pywebview window'
        return
    }
    if ($EDGE) {
        Start-Process -FilePath $EDGE -ArgumentList @(
            "--app=$Target", '--no-first-run', '--no-default-browser-check',
            '--window-size=1280,900')
        Trace 'opened Edge app window (fallback)'
    } else {
        Start-Process $Target
    }
}

function Get-Listener {
    (Get-NetTCPConnection -LocalPort 8770 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1).OwningProcess
}

$existing = Get-Listener
if ($existing) {
    Trace "already running, listener=$existing"
    Open-AppWindow -Target $URL
    Start-Sleep -Seconds 2
    exit 0
}

Trace 'starting server.py'
# Hidden 避免 py.exe 弹出控制台黑框；stdout/stderr 重定向到日志便于诊断。
# 注意：PowerShell 7 下若环境变量存在大小写重复（如 http_proxy/HTTP_PROXY），
# Start-Process 会抛 ArgumentException 而静默失败 —— 脚本开头已做去重处理。
Start-Process -FilePath 'py' -ArgumentList '-3.13', 'server.py' `
    -WorkingDirectory $APP -WindowStyle Hidden `
    -RedirectStandardOutput $LOG -RedirectStandardError "$LOG.err"

# Wait for the port, then record the pid so the stop script targets this exact
# process rather than any python that happens to hold the port later.
$up = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 500
    $p = Get-Listener
    if ($p) { $p | Out-File -FilePath $PIDF -Encoding ascii -NoNewline; $up = $true; break }
}
Trace "server up=$up pid=$(Get-Content $PIDF -Raw -ErrorAction SilentlyContinue)"

if ($up) {
    Open-AppWindow -Target $URL
} else {
    Trace "TIMEOUT, see $LOG"
}
Start-Sleep -Seconds 2
