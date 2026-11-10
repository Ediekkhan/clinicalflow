param([Parameter(Mandatory=$true)][string]$InputFile)
$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $InputFile)) { throw "Backup file not found: $InputFile" }
pg_restore --clean --if-exists --no-owner --dbname $env:DATABASE_URL $InputFile
Write-Output "Restore completed from $InputFile"
