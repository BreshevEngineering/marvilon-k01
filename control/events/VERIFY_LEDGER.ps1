param(
    [string]$RepoRoot = "",
    [switch]$VerboseOutput
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$ledger = Join-Path $RepoRoot "control\events\engineering_events.jsonl"

if (-not (Test-Path -LiteralPath $ledger -PathType Leaf)) {
    if ($VerboseOutput) {
        Write-Host "Ledger does not exist yet."
    }
    exit 0
}

function ShaText([string]$s) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString(
            $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($s))
        ).Replace("-", "").ToLowerInvariant())
    }
    finally {
        $sha.Dispose()
    }
}

$prev = ""
$expectedSeq = 1
$errors = @()

foreach ($line in Get-Content -LiteralPath $ledger -Encoding UTF8) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }

    $e = $line | ConvertFrom-Json

    if ([int]$e.seq -ne $expectedSeq) {
        $errors += "seq mismatch expected=$expectedSeq actual=$($e.seq)"
    }

    if ([string]$e.previous_hash -ne $prev) {
        $errors += "previous_hash mismatch at seq=$($e.seq)"
    }

    $base = [ordered]@{
        schema        = $e.schema
        seq           = [int]$e.seq
        timestamp     = $e.timestamp
        type          = $e.type
        subject       = $e.subject
        payload       = $e.payload
        previous_hash = $e.previous_hash
    }

    $canonical = ($base | ConvertTo-Json -Depth 30 -Compress)
    $actual = ShaText ($prev + "|" + $canonical)

    if ($actual -ne [string]$e.event_hash) {
        $errors += "event_hash mismatch at seq=$($e.seq)"
    }

    $prev = [string]$e.event_hash
    $expectedSeq++
}

if ($errors.Count -gt 0) {
    if ($VerboseOutput) {
        $errors | ForEach-Object { Write-Host ("FAIL " + $_) -ForegroundColor Red }
    }
    exit 2
}

if ($VerboseOutput) {
    Write-Host "PASS hash-chain events=$($expectedSeq-1) tail=$prev"
}

exit 0
