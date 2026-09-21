$ErrorActionPreference = "Stop"
$Repo = "D:\BreshevEngineering\marvilon-k01"
$RuntimeModule = Join-Path $Repo "cad_api\solidworks_2018_proven\runtime_core\K01_SW2018_RUNTIME_CORE.psm1"
$RuntimeCs = Join-Path $Repo "cad_api\solidworks_2018_proven\runtime_core\K01SwRuntimeCore.cs"
$RefineCs = Join-Path $Repo "cad_api\solidworks_2018_proven\drawing_refine\K01DrawingRefineApi.cs"

if ($args.Count -lt 1) {
    Write-Host "Usage: RUN_K01_DRAWING_REFINE_API.cmd <job.json>"
    exit 2
}
$Job = (Resolve-Path -LiteralPath $args[0]).Path
$ReportDir = Join-Path $Repo "reports\drawing\refine_api_current"
$BuildDir = Join-Path $ReportDir "build"

Import-Module $RuntimeModule -Force -WarningAction SilentlyContinue
Write-Host "=== K01 DRAWING REFINE API V1 ==="
Write-Host "JOB=$Job"
Write-Host "POLICY=EXACT TARGET ONLY / CANDIDATE COPY / NO GLOBAL SW-CLOSED REQUIREMENT"

# Defensive contract: runtime helper must return one executable path and nothing else.
$buildResult = @(Build-K01Sw2018Helper -Sources @($RuntimeCs,$RefineCs) -BuildDir $BuildDir -ExeName "K01DrawingRefineApi.exe")
if ($buildResult.Count -ne 1) {
    throw "RUNTIME_CORE_RETURN_CONTRACT_FAILED: expected exactly one executable path, got $($buildResult.Count)"
}
$exe = [string]$buildResult[0]
if ([String]::IsNullOrWhiteSpace($exe) -or !(Test-Path -LiteralPath $exe)) {
    throw "RUNTIME_CORE_EXE_MISSING: $exe"
}
Write-Host "BUILD_RUNTIME_PROBE=PASS"
Write-Host "REFINE_EXE=$exe"

Push-Location $BuildDir
try {
    & $exe "$Job" "$ReportDir"
    $rc=$LASTEXITCODE
} finally { Pop-Location }

Write-Host "RC=$rc"
exit $rc
