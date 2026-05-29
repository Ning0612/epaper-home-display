#Requires -Version 5.1
<#
.SYNOPSIS
  Install ai-usage-collector and register a Windows Task Scheduler job (every 3 min).
.DESCRIPTION
  1. Verifies .env exists
  2. npm install + npm run build
  3. Creates logs\ directory and a run.cmd wrapper (for log capture)
  4. Registers "ai-usage-collector" in Task Scheduler
  Run once from the project root or from the scripts\ directory.
  To remove: scripts\uninstall-windows.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Require admin (Task Scheduler needs it) ────────────────────────────────────
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Host "[setup] Restarting with administrator privileges..."
    $psArgs = "-ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`""
    Start-Process powershell -Verb RunAs -ArgumentList $psArgs -Wait
    exit
}

# ── Resolve paths ──────────────────────────────────────────────────────────────
$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir          # tools/ai-usage-collector

Write-Host "[setup] Project dir: $projectDir"

# ── Guard: .env must exist ─────────────────────────────────────────────────────
$envFile = Join-Path $projectDir ".env"
if (-not (Test-Path $envFile)) {
    Write-Warning ".env not found. Copy .env.example → .env and set PI_URL first."
    Write-Warning "  Copy-Item `"$projectDir\.env.example`" `"$envFile`""
    exit 1
}

# ── npm install + build ────────────────────────────────────────────────────────
Push-Location $projectDir
try {
    Write-Host "[setup] Installing npm dependencies..."
    npm install --prefer-offline
    Write-Host "[setup] Building TypeScript..."
    npm run build
} finally {
    Pop-Location
}

# ── Verify compiled entry point ────────────────────────────────────────────────
$distEntry = Join-Path $projectDir "dist\index.js"
if (-not (Test-Path $distEntry)) {
    Write-Error "Build failed: $distEntry not found."
    exit 1
}

# ── Create logs directory ──────────────────────────────────────────────────────
$logsDir = Join-Path $projectDir "logs"
New-Item -ItemType Directory -Force $logsDir | Out-Null

# ── Create run.cmd wrapper (enables log capture in Task Scheduler) ─────────────
$runCmd = Join-Path $projectDir "scripts\run.cmd"
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    Write-Error "node.exe not found in PATH. Install Node.js first."
    exit 1
}
$nodeExe = $nodeCmd.Source
$logFile = Join-Path $logsDir "collector.log"
@"
@echo off
cd /d "$projectDir"
"$nodeExe" dist\index.js >> "$logFile" 2>&1
"@ | Set-Content $runCmd -Encoding ascii

Write-Host "[setup] Created wrapper: $runCmd"

# ── Register Task Scheduler (XML — compatible with PS 5.1) ────────────────────
$taskName = "ai-usage-collector"
$startBoundary = (Get-Date).AddSeconds(10).ToString("yyyy-MM-ddTHH:mm:ss")

# Escape XML special chars in paths
$runCmdXml  = [System.Security.SecurityElement]::Escape($runCmd)
$projectXml = [System.Security.SecurityElement]::Escape($projectDir)

$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <TimeTrigger>
      <Repetition>
        <Interval>PT3M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>$startBoundary</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>cmd.exe</Command>
      <Arguments>/c "$runCmdXml"</Arguments>
      <WorkingDirectory>$projectXml</WorkingDirectory>
    </Exec>
  </Actions>
  <Settings>
    <ExecutionTimeLimit>PT2M</ExecutionTimeLimit>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
  </Settings>
  <Principals>
    <Principal id="Author">
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
</Task>
"@

Register-ScheduledTask -TaskName $taskName -Xml $xml -Force | Out-Null

Write-Host "[setup] Registered Task Scheduler: '$taskName' (every 3 min)"
Write-Host "[setup] Logs: $logFile"
Write-Host "[setup] Done. Use scripts\uninstall-windows.ps1 to remove."
