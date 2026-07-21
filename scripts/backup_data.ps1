param(
    [string]$Source = ".\data",
    [string]$OutputDir = ".\backups"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Source)) {
    throw "Data folder not found: $Source"
}

$resolvedSource = Resolve-Path -LiteralPath $Source
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$archivePath = Join-Path $OutputDir "data-$timestamp.zip"
Compress-Archive -Path (Join-Path $resolvedSource "*") -DestinationPath $archivePath -Force

Write-Output "Backup created: $archivePath"
