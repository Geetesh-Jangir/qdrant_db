# Download scrape outputs from R2 to cloudflare/output/
param(
    [string]$Bucket = "news-scrape-data",
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
if (-not $OutDir) {
    $OutDir = Join-Path (Split-Path $PSScriptRoot -Parent) "output"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

foreach ($key in @("output/scraped_articles.json", "output/scrape_errors.json", "output/run_state.json")) {
    $name = Split-Path $key -Leaf
    $dest = Join-Path $OutDir $name
    Write-Host "Getting $key ..."
    wrangler r2 object get "$Bucket/$key" --file $dest
}
Write-Host "Saved under $OutDir"
