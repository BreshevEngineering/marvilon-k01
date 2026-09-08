param([string]$RepoRoot = "")

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function FileCheck {
    param([string]$Id, [string]$RelativePath)

    $path = Join-Path $RepoRoot $RelativePath
    return [pscustomobject]@{
        id    = $Id
        path  = $path
        pass  = (Test-Path -LiteralPath $path -PathType Leaf)
        error = ""
    }
}

function JsonCheck {
    param([string]$Id, [string]$RelativePath)

    $path = Join-Path $RepoRoot $RelativePath
    $ok = $false
    $errorText = ""

    if (Test-Path -LiteralPath $path -PathType Leaf) {
        try {
            Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json | Out-Null
            $ok = $true
        }
        catch {
            $errorText = $_.Exception.Message
        }
    }
    else {
        $errorText = "File missing"
    }

    return [pscustomobject]@{
        id    = $Id
        path  = $path
        pass  = $ok
        error = $errorText
    }
}

function PowerShellSyntaxCheck {
    param([string]$Id, [string]$RelativePath)

    $path = Join-Path $RepoRoot $RelativePath
    $ok = $false
    $errorText = ""

    if (Test-Path -LiteralPath $path -PathType Leaf) {
        $tokens = $null
        $parseErrors = $null
        [Management.Automation.Language.Parser]::ParseFile(
            $path,
            [ref]$tokens,
            [ref]$parseErrors
        ) | Out-Null

        $ok = ($parseErrors.Count -eq 0)
        if (-not $ok) {
            $errorText = ($parseErrors | ForEach-Object { $_.Message }) -join " | "
        }
    }
    else {
        $errorText = "File missing"
    }

    return [pscustomobject]@{
        id    = $Id
        path  = $path
        pass  = $ok
        error = $errorText
    }
}

$checks = @()

$requiredFiles = @(
    "control\command_center\index.html",
    "control\command_center\styles.css",
    "control\command_center\app.js",
    "control\command_center\core.ps1",
    "control\command_center\server.ps1",
    "control\command_center\OPEN_K01_COMMAND_CENTER.cmd",
    "control\requirements\requirements.json",
    "control\state\reducer_core.ps1",
    "control\state\reducer.ps1",
    "control\provenance\REGISTER_EVIDENCE.ps1",
    "control\events\APPEND_EVENT.ps1",
    "control\configuration\revision_policy.json",
    "control\drawings\tpd_automation_architecture.json",
    "control\bom\bom_policy.json",
    "tests\run_reducer_tests.ps1",
    "tests\run_core_tests.ps1"
)

foreach ($relative in $requiredFiles) {
    $checks += FileCheck ("FILE:" + $relative) $relative
}

$jsonFiles = @(
    "control\requirements\requirements.json",
    "control\configuration\revision_policy.json",
    "control\drawings\tpd_automation_architecture.json",
    "control\drawings\drawing_v3_rejection.json",
    "control\bom\bom_policy.json"
)

foreach ($relative in $jsonFiles) {
    $checks += JsonCheck ("JSON:" + $relative) $relative
}

$powerShellFiles = @(
    "control\command_center\core.ps1",
    "control\command_center\server.ps1",
    "control\state\reducer_core.ps1",
    "control\state\reducer.ps1",
    "control\provenance\REGISTER_EVIDENCE.ps1",
    "control\provenance\VERIFY_PROVENANCE.ps1",
    "control\events\APPEND_EVENT.ps1",
    "control\events\VERIFY_LEDGER.ps1",
    "tests\run_reducer_tests.ps1",
    "tests\run_core_tests.ps1"
)

foreach ($relative in $powerShellFiles) {
    $checks += PowerShellSyntaxCheck ("PS:" + $relative) $relative
}

$staticFailures = @($checks | Where-Object { -not $_.pass })

if ($staticFailures.Count -eq 0) {
    $coreTests = Join-Path $RepoRoot "tests\run_core_tests.ps1"
    & $coreTests
    $coreTestExit = $LASTEXITCODE

    $checks += [pscustomobject]@{
        id    = "RUNTIME:CORE_TESTS"
        path  = $coreTests
        pass  = ($coreTestExit -eq 0)
        error = $(if ($coreTestExit -eq 0) { "" } else { "Core tests exit code $coreTestExit" })
    }
}

$failures = @($checks | Where-Object { -not $_.pass })
$status = $(if ($failures.Count -eq 0) { "PASS_INFRASTRUCTURE" } else { "HOLD" })

$out = Join-Path $RepoRoot "reports\control\K01_MEDTAS_PREFLIGHT_CURRENT.json"
New-Item ([IO.Path]::GetDirectoryName($out)) -ItemType Directory -Force | Out-Null

[pscustomobject]@{
    schema   = "k01.medtas_preflight.v2"
    created  = (Get-Date).ToString("o")
    status   = $status
    failures = $failures.Count
    checks   = $checks
} | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $out -Encoding UTF8

Write-Host ""
Write-Host "MEDTAS preflight: $status | failures=$($failures.Count)"

foreach ($failure in $failures) {
    Write-Host ("FAIL " + $failure.id + " :: " + $failure.error) -ForegroundColor Red
}

if ($failures.Count -gt 0) {
    exit 2
}

exit 0
