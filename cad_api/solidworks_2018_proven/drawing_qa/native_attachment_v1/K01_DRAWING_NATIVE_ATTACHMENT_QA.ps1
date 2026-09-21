$ErrorActionPreference = "Stop"
$Repo = "D:\BreshevEngineering\marvilon-k01"
$RuntimeModule = Join-Path $Repo "cad_api\solidworks_2018_proven\runtime_core\K01_SW2018_RUNTIME_CORE.psm1"
$RuntimeCs = Join-Path $Repo "cad_api\solidworks_2018_proven\runtime_core\K01SwRuntimeCore.cs"
$QaCs = Join-Path $Repo "cad_api\solidworks_2018_proven\drawing_qa\native_attachment_v1\K01DrawingNativeAttachmentQaV1.cs"
$ReportDir = Join-Path $Repo "reports\drawing\native_attachment_qa_current"
$BuildDir = Join-Path $ReportDir "build"

Import-Module $RuntimeModule -Force -WarningAction SilentlyContinue

$buildResult = @(Build-K01Sw2018Helper -Sources @($RuntimeCs,$QaCs) -BuildDir $BuildDir -ExeName "K01DrawingNativeAttachmentQaV1.exe")
if ($buildResult.Count -ne 1) { throw "RUNTIME_CORE_RETURN_CONTRACT_FAILED count=$($buildResult.Count)" }
$exe = [string]$buildResult[0]
if ([String]::IsNullOrWhiteSpace($exe) -or !(Test-Path -LiteralPath $exe)) { throw "QA_EXE_MISSING: $exe" }

if ($args.Count -eq 1 -and $args[0] -eq "--runtime-probe") {
    Write-Host "STATUS=PASS_NATIVE_ATTACHMENT_QA_COMPILE_PREFLIGHT"
    Write-Host "QA_EXE=$exe"
    exit 0
}

if ($args.Count -ge 2 -and $args[0] -eq "--inventory") {
    $drawing = (Resolve-Path -LiteralPath $args[1]).Path
    Push-Location $BuildDir
    try {
        & $exe "--inventory" "$drawing" "$ReportDir"
        $rc=$LASTEXITCODE
    } finally { Pop-Location }
    exit $rc
}

if ($args.Count -ge 2 -and $args[0] -eq "--verify") {
    $job = (Resolve-Path -LiteralPath $args[1]).Path
    Push-Location $BuildDir
    try {
        & $exe "--verify" "$job" "$ReportDir"
        $rc=$LASTEXITCODE
    } finally { Pop-Location }
    exit $rc
}

Write-Host "Usage:"
Write-Host "  ...ps1 --runtime-probe"
Write-Host "  ...ps1 --inventory <drawing.slddrw>"
Write-Host "  ...ps1 --verify <job.json>"
exit 2
