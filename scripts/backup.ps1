# Daily backup. Schedule via Task Scheduler:
#   schtasks /Create /SC DAILY /TN "event-traffic-backup" /TR "powershell -F C:\path\scripts\backup.ps1" /ST 02:00
param(
  [string]$DestDir = "$PSScriptRoot\..\backups",
  [int]$RetentionDays = 30
)
$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $PSScriptRoot
$Stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$Archive = Join-Path $DestDir "event-traffic-$Stamp.zip"
New-Item -ItemType Directory -Force -Path $DestDir | Out-Null

Compress-Archive -Path @(
  (Join-Path $Project "data\processed"),
  (Join-Path $Project "data\rag"),
  (Join-Path $Project "models"),
  (Join-Path $Project "logs")
) -DestinationPath $Archive -Force

Write-Host "wrote $Archive  ($([math]::Round((Get-Item $Archive).Length / 1MB, 1)) MB)"

# Prune older than retention
Get-ChildItem $DestDir -Filter "event-traffic-*.zip" |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$RetentionDays) } |
  Remove-Item -Force
