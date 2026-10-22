# Re-scrape URLs that failed with HTTP 403 in scrape_errors.json (paced Worker batches).
param(
    [Parameter(Mandatory = $false)]
    [string]$WorkerUrl = "",
    [string]$ErrorsFile = "",
    [string]$Secret = "",
    [int]$BatchSize = 5,
    [int]$MaxItems = 0,
    [int]$DelaySec = 8
)

$ErrorActionPreference = "Stop"
$CloudflareRoot = Split-Path $PSScriptRoot -Parent
$OutDir = Join-Path $CloudflareRoot "output"

if (-not $ErrorsFile) {
    $ErrorsFile = Join-Path $OutDir "scrape_errors.json"
}
if (-not $WorkerUrl) {
    $urlFile = Join-Path $CloudflareRoot "worker-url.txt"
    if (Test-Path $urlFile) {
        $WorkerUrl = (Get-Content $urlFile -Raw).Trim()
    }
}
if (-not $WorkerUrl) {
    Write-Host "Set -WorkerUrl or create cloudflare\worker-url.txt"
    exit 1
}
$WorkerUrl = $WorkerUrl.TrimEnd("/")

if (-not (Test-Path $ErrorsFile)) {
    Write-Host "Errors file not found: $ErrorsFile"
    Write-Host "Run run-scrape-local.ps1 first or point -ErrorsFile to your scrape_errors.json"
    exit 1
}

$data = Get-Content $ErrorsFile -Raw -Encoding UTF8 | ConvertFrom-Json
$allItems = @(
    $data.items |
    Where-Object { $_.http_status -eq 403 -and $_.url -and $_.url.Trim() } |
    ForEach-Object {
        @{
            url = $_.url
            title = $_.title
            source = $_.source
            drop_reason = if ($_.drop_reason) { $_.drop_reason } else { "fetch_failed" }
            last_error = if ($_.message) { $_.message } else { $_.detail }
            retriable = $false
        }
    }
)

if ($MaxItems -gt 0) {
    $allItems = $allItems | Select-Object -First $MaxItems
}
$total = $allItems.Count
Write-Host "403 retry input: $ErrorsFile ($total URLs with http_status=403)"
Write-Host "Worker: $WorkerUrl (batch=$BatchSize, delay=$DelaySec sec between batches)"

if ($total -eq 0) {
    Write-Host "No 403 rows to process."
    exit 0
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$runId = "403retry_{0:yyyyMMddTHHmmssZ}" -f [DateTime]::UtcNow
$scrapedItems = [System.Collections.Generic.List[object]]::new()
$errorItems = [System.Collections.Generic.List[object]]::new()
$runSummaries = [System.Collections.Generic.List[object]]::new()

$headers = @{ "Content-Type" = "application/json" }
if ($Secret) {
    $headers["Authorization"] = "Bearer $Secret"
}

$offset = 0
$batchNum = 0
while ($offset -lt $total) {
    $batchNum++
    $slice = $allItems[$offset..([Math]::Min($offset + $BatchSize - 1, $total - 1))]
    $body = @{
        items = $slice
        run_id = $runId
        source_key = $ErrorsFile
    } | ConvertTo-Json -Depth 20 -Compress

    Write-Host "Batch $batchNum offset=$offset count=$($slice.Count) ..."
    try {
        $resp = Invoke-RestMethod -Method POST -Uri "$WorkerUrl/run" -Headers $headers -Body $body
    } catch {
        Write-Host "Request failed: $_"
        if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message }
        exit 1
    }

    if (-not $resp.ok) {
        Write-Host "Worker error: $($resp | ConvertTo-Json -Depth 5)"
        exit 1
    }

    foreach ($row in $resp.scraped.items) { $scrapedItems.Add($row) }
    foreach ($row in $resp.errors.items) { $errorItems.Add($row) }
    if ($resp.run_summary) { $runSummaries.Add($resp.run_summary) }

    $offset += $slice.Count
    if ($DelaySec -gt 0 -and $offset -lt $total) {
        Start-Sleep -Seconds $DelaySec
    }
}

function Summarize-Scraped($items) {
    $ok = ($items | Where-Object { $_.status -eq "ok" }).Count
    $thin = ($items | Where-Object { $_.status -eq "extract_thin" }).Count
    return @{ total_ok = $ok; total_thin = $thin }
}

function Summarize-Errors($items) {
    $byCode = @{}
    $byStatus = @{}
    foreach ($e in $items) {
        if ($e.error_code) {
            if (-not $byCode.ContainsKey($e.error_code)) { $byCode[$e.error_code] = 0 }
            $byCode[$e.error_code]++
        }
        $st = if ($null -eq $e.http_status) { "none" } else { [string]$e.http_status }
        if (-not $byStatus.ContainsKey($st)) { $byStatus[$st] = 0 }
        $byStatus[$st]++
    }
    return @{
        attempted = $items.Count
        failed = $items.Count
        by_error_code = $byCode
        by_http_status = $byStatus
    }
}

$now = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
$scrapedPath = Join-Path $OutDir "scraped_403_retry.json"
$errorsPath = Join-Path $OutDir "scrape_403_remaining_errors.json"
$statePath = Join-Path $OutDir "run_403_state.json"

$scrapedDoc = @{
    schema = "cloudflare-scrape/v1"
    generated_at = $now
    run_id = $runId
    source_key = $ErrorsFile
    filter = "http_status=403"
    items = $scrapedItems
    summary = Summarize-Scraped $scrapedItems
}
$errorsDoc = @{
    schema = "cloudflare-scrape-errors/v1"
    generated_at = $now
    run_id = $runId
    source_key = $ErrorsFile
    filter = "http_status=403"
    items = $errorItems
    summary = Summarize-Errors $errorItems
}
$stateDoc = @{
    offset = $total
    total = $total
    run_id = $runId
    updated_at = $now
    completed = $true
    batch_summaries = $runSummaries
}

$scrapedDoc | ConvertTo-Json -Depth 30 | Set-Content -Path $scrapedPath -Encoding UTF8
$errorsDoc | ConvertTo-Json -Depth 30 | Set-Content -Path $errorsPath -Encoding UTF8
$stateDoc | ConvertTo-Json -Depth 30 | Set-Content -Path $statePath -Encoding UTF8

Write-Host ""
Write-Host "Done (403 retry run)."
Write-Host "  Recovered: $($scrapedItems.Count) -> $scrapedPath"
Write-Host "  Still failed: $($errorItems.Count) -> $errorsPath"
Write-Host "  OK: $($scrapedDoc.summary.total_ok)  thin: $($scrapedDoc.summary.total_thin)"
