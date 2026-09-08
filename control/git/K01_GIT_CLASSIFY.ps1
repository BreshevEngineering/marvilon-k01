param([string]$RepoRoot = "")

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Classify-Path {
    param([string]$Path)

    $p = $Path.Replace("/", "\")

    if ($p -match '(^|\\)(bin|obj|__pycache__|\.pytest_cache)(\\|$)' -or
        $p -match '\.(log|tmp|bak|pyc)$' -or
        $p -match '^handoff\\current\\' -or
        $p -match '^reports\\.*\\current\\' -or
        $p -match '^reports\\cad\\live\\') {
        return "GENERATED_LOCAL"
    }

    if ($p -match '^(\.github|control|cad_api|tests|tools|scripts|spec|master|params)(\\|$)' -or
        $p -match '^(README|CHANGELOG|pyproject\.toml|\.gitignore|\.gitattributes)') {
        return "SOURCE_CONTROL_CANDIDATE"
    }

    if ($p -match '^(bom|docs|reference|review_upload|handoff|reports)(\\|$)') {
        return "REVIEW_REQUIRED"
    }

    return "REVIEW_REQUIRED"
}

$git = Get-Command git.exe -ErrorAction Stop
$statusText = (& $git.Source -C $RepoRoot status --porcelain=v1 --untracked-files=all 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "git status failed: $statusText"
}

$items = @()
if (-not [string]::IsNullOrWhiteSpace($statusText)) {
    foreach ($line in ($statusText -split "`r?`n")) {
        if ($line.Length -lt 4) { continue }

        $xy = $line.Substring(0, 2)
        $path = $line.Substring(3).Trim()

        if ($path -match ' -> ') {
            $path = ($path -split ' -> ')[-1].Trim()
        }

        $items += [pscustomobject]@{
            xy       = $xy
            path     = $path
            category = Classify-Path $path
        }
    }
}

$categories = [ordered]@{
    GENERATED_LOCAL           = @($items | Where-Object { $_.category -eq "GENERATED_LOCAL" }).Count
    REVIEW_REQUIRED           = @($items | Where-Object { $_.category -eq "REVIEW_REQUIRED" }).Count
    SOURCE_CONTROL_CANDIDATE  = @($items | Where-Object { $_.category -eq "SOURCE_CONTROL_CANDIDATE" }).Count
}

$untracked = @($items | Where-Object { $_.xy -eq "??" }).Count
$readiness = if ($categories.REVIEW_REQUIRED -eq 0) { "READY_FOR_CHECKPOINT_REVIEW" } else { "HOLD_REVIEW_REQUIRED" }

$report = [pscustomobject]@{
    schema      = "k01.git_classification.v3"
    created     = (Get-Date).ToString("o")
    status      = "PASS_READ_ONLY_CLASSIFICATION"
    readiness   = $readiness
    repo_root   = $RepoRoot
    dirty       = $items.Count
    untracked   = $untracked
    categories  = $categories
    generated_local = @($items | Where-Object { $_.category -eq "GENERATED_LOCAL" })
    review_required = @($items | Where-Object { $_.category -eq "REVIEW_REQUIRED" })
    source_control_candidate = @($items | Where-Object { $_.category -eq "SOURCE_CONTROL_CANDIDATE" })
    policy      = "READ ONLY. No git add, commit, push, reset, clean or checkout is executed."
}

$out = Join-Path $RepoRoot "reports\git\K01_GIT_CLASSIFICATION_CURRENT.json"
New-Item ([IO.Path]::GetDirectoryName($out)) -ItemType Directory -Force | Out-Null
$report | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $out -Encoding UTF8

Write-Host "Git classification: dirty=$($report.dirty) untracked=$($report.untracked) readiness=$readiness"
foreach ($k in $categories.Keys) {
    Write-Host ("  {0,-26} = {1}" -f $k, $categories[$k])
}
Write-Host "Report: $out"
exit 0
