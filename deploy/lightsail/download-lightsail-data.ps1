# Mirror pipeline data from Lightsail into repo lightsail_logs/lightsail_complete/
# Usage (PowerShell): .\deploy\lightsail\download-lightsail-data.ps1
# Optional: -LightsailIp 1.2.3.4 -Key C:\path\to.pem

param(
    [string]$LightsailIp = "13.201.64.68",
    [string]$SshUser = "ubuntu",
    [string]$Key = "$env:USERPROFILE\Downloads\LightsailDefaultKey-ap-south-1.pem",
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
)

$ErrorActionPreference = "Stop"
$RemoteData = "/opt/news-rag/data"
$Stage = Join-Path $env:TEMP "lightsail_data_dl"
$Dest = Join-Path $RepoRoot "lightsail_logs\lightsail_complete"

$dirs = @("news_failures", "news_runs", "news_runs_daily", "news_backfill")

New-Item -ItemType Directory -Force -Path $Stage | Out-Null
New-Item -ItemType Directory -Force -Path $Dest | Out-Null

foreach ($name in $dirs) {
    Write-Host "scp $name ..."
    scp -i $Key -r "${SshUser}@${LightsailIp}:${RemoteData}/${name}" $Stage
}

Copy-Item -Path (Join-Path $Stage "*") -Destination $Dest -Recurse -Force
Remove-Item -Path $Stage -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "`nDone -> $Dest"
Get-ChildItem $Dest -Directory | ForEach-Object {
    $files = Get-ChildItem $_.FullName -Recurse -File
    $sum = ($files | Measure-Object -Property Length -Sum).Sum
    Write-Host ("  {0}: {1} files, {2:N2} MB" -f $_.Name, $files.Count, ($sum / 1MB))
}
Write-Host "`nfailed_source.json copies:"
Get-ChildItem $Dest -Recurse -Filter "failed_source.json" | ForEach-Object {
    Write-Host ("  {0} ({1:N0} bytes)" -f $_.FullName.Replace($Dest + "\", ""), $_.Length)
}
Write-Host "`nFull scrape-failure ledger (use for retries): news_failures\source.json"
