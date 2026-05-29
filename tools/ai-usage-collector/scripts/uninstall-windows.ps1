#Requires -Version 5.1
<#
.SYNOPSIS
  Remove the "ai-usage-collector" Task Scheduler job.
#>

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Host "[uninstall] Restarting with administrator privileges..."
    $psArgs = "-ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`""
    Start-Process powershell -Verb RunAs -ArgumentList $psArgs -Wait
    exit
}

$taskName = "ai-usage-collector"

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "[uninstall] Removed Task Scheduler: '$taskName'"
} else {
    Write-Host "[uninstall] Task '$taskName' not found — nothing to remove."
}
