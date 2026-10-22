# Upload local failed_sources JSON to R2 (input for the scrape Worker).
# Prereq: wrangler login, bucket created (see ../README.md)

param(
    [string]$File = "",
    [string]$Bucket = "news-scrape-data",
    [string]$ObjectKey = "input/failed_sources.json"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$DefaultFile = Join-Path $RepoRoot "cloudflare\input\failed_sources.json"

if (-not $File) {
    $File = $DefaultFile
}
if (-not (Test-Path $File)) {
    Write-Host "File not found: $File"
    Write-Host "Copy Lightsail news_failures/source.json to cloudflare\input\failed_sources.json first."
    exit 1
}

Write-Host "Uploading $File -> r2://$Bucket/$ObjectKey"
wrangler r2 object put "$Bucket/$ObjectKey" --file $File
Write-Host "Done."
