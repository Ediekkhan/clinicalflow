param([string]$Output = "backups\clinicalflow-$(Get-Date -Format yyyyMMdd-HHmmss).dump")
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force (Split-Path $Output) | Out-Null
pg_dump --format=custom --no-owner --file $Output $env:DATABASE_URL
Write-Output "Backup written to $Output"
