$ErrorActionPreference = "Stop"
$Repo = "D:\BreshevEngineering\marvilon-k01"
$RuntimeModule = Join-Path $Repo "cad_api\solidworks_2018_proven\runtime_core\K01_SW2018_RUNTIME_CORE.psm1"
$RuntimeCs = Join-Path $Repo "cad_api\solidworks_2018_proven\runtime_core\K01SwRuntimeCore.cs"
$ApiCs = Join-Path $Repo "cad_api\solidworks_2018_proven\drawing_annotate_existing_v1\K01DrawingAnnotateExistingV1.cs"
$ReportDir = Join-Path $Repo "reports\drawing\annotate_existing_v1"
$BuildDir = Join-Path $ReportDir "build"

Import-Module $RuntimeModule -Force -WarningAction SilentlyContinue

$buildResult = @(Build-K01Sw2018Helper -Sources @($RuntimeCs,$ApiCs) -BuildDir $BuildDir -ExeName "K01DrawingAnnotateExistingV1.exe")
if ($buildResult.Count -ne 1) { throw "RUNTIME_CORE_RETURN_CONTRACT_FAILED count=$($buildResult.Count)" }
$exe = [string]$buildResult[0]
if ([String]::IsNullOrWhiteSpace($exe) -or !(Test-Path -LiteralPath $exe)) { throw "ANNOTATE_EXE_MISSING: $exe" }

if ($args.Count -eq 1 -and $args[0] -eq "--runtime-probe") {
    Write-Host "STATUS=PASS_DRAWING_ANNOTATE_EXISTING_V1_COMPILE_PREFLIGHT"
    Write-Host "EXE=$exe"
    exit 0
}

if ($args.Count -lt 1) {
    Write-Host "Usage: ...ps1 <job.json>"
    exit 2
}

$job = (Resolve-Path -LiteralPath $args[0]).Path
Push-Location $BuildDir
try {
    & $exe "$job" "$ReportDir"
    $rc=$LASTEXITCODE
} finally { Pop-Location }
exit $rc
