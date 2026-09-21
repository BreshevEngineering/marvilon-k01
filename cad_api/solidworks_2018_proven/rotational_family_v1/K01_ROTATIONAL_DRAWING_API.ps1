$ErrorActionPreference = "Stop"
$Repo = "D:\BreshevEngineering\marvilon-k01"

if ($args.Count -lt 1) {
    Write-Host "Usage: RUN_K01_ROTATIONAL_DRAWING_API.cmd <drawing-spec.json>"
    exit 2
}

$Spec = (Resolve-Path -LiteralPath $args[0]).Path
$RuntimeModule = Join-Path $Repo "cad_api\solidworks_2018_proven\runtime_core\K01_SW2018_RUNTIME_CORE.psm1"
$BuilderCs = Join-Path $Repo "cad_api\solidworks_2018_proven\current\K01_DRAWING_SYSTEM_V1\K01DrawingSystemV1.cs"
$RunRoot = Join-Path $Repo "reports\drawing\rotational_family_v1"
$BuildDir = Join-Path $RunRoot "build"
$Report = Join-Path $RunRoot "K01_ROTATIONAL_DRAWING_BUILD_CURRENT.txt"
$Stdout = Join-Path $RunRoot "K01_ROTATIONAL_DRAWING_BUILD_STDOUT_CURRENT.txt"

New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
Import-Module $RuntimeModule -Force -WarningAction SilentlyContinue

$sld = Get-K01Sw2018Interop "SolidWorks.Interop.sldworks.dll"
$con = Get-K01Sw2018Interop "SolidWorks.Interop.swconst.dll"
$csc = Get-K01Csc
$exe = Join-Path $BuildDir "K01DrawingSystemV1.exe"

Remove-Item -LiteralPath $exe -Force -ErrorAction SilentlyContinue

$cargs = @(
    "/nologo",
    "/langversion:5",
    "/target:exe",
    "/platform:x64",
    "/optimize+",
    "/r:$sld",
    "/r:$con",
    "/r:System.Web.Extensions.dll",
    "/out:$exe",
    $BuilderCs
)

$compile = @(& $csc @cargs)
$crc = $LASTEXITCODE
foreach ($line in $compile) { Write-Host $line }
if ($crc -ne 0 -or !(Test-Path -LiteralPath $exe)) {
    Write-Host "STATUS=HOLD_ROTATIONAL_DRAWING_BUILDER_COMPILE"
    exit 2
}

Copy-Item -LiteralPath $sld -Destination (Join-Path $BuildDir "SolidWorks.Interop.sldworks.dll") -Force
Copy-Item -LiteralPath $con -Destination (Join-Path $BuildDir "SolidWorks.Interop.swconst.dll") -Force

Write-Host "BUILDER_COMPILE=PASS"
Write-Host "SPEC=$Spec"

Push-Location $BuildDir
try {
    $nativeOut = @(& $exe "--spec" "$Spec" "--report" "$Report" "--mode" "review")
    $nativeRc = $LASTEXITCODE
} finally {
    Pop-Location
}

$nativeOut | Set-Content -LiteralPath $Stdout -Encoding UTF8
foreach ($line in $nativeOut) { Write-Host $line }

$dwg = $null
$pdf = $null
$dxf = $null
$bmp = $null

foreach ($line in $nativeOut) {
    if ($line -match '^DRAWING:\s*(.+)$') { $dwg = $Matches[1].Trim() }
    elseif ($line -match '^PDF:\s*(.+)$') { $pdf = $Matches[1].Trim() }
    elseif ($line -match '^DXF:\s*(.+)$') { $dxf = $Matches[1].Trim() }
    elseif ($line -match '^REPORT:\s*(.+)$') { $Report = $Matches[1].Trim() }
}

$artifactCount = 0
foreach ($p in @($dwg,$pdf,$dxf)) {
    if ($p -and (Test-Path -LiteralPath $p)) { $artifactCount++ }
}

Write-Host "NATIVE_RC=$nativeRc"
Write-Host "ARTIFACT_COUNT=$artifactCount"

if ($artifactCount -ge 2) {
    if ($nativeRc -eq 0) {
        Write-Host "STATUS=PASS_ROTATIONAL_DRAWING_ARTIFACT_GENERATED"
    } else {
        Write-Host "STATUS=PASS_ROTATIONAL_DRAWING_ARTIFACT_GENERATED_WITH_PARTIAL_AUTHORING"
    }
    Write-Host "MANUAL_FINISH=AUTHORIZED"
    Write-Host "DRAWING=$dwg"
    Write-Host "PDF=$pdf"
    Write-Host "DXF=$dxf"
    Write-Host "REPORT=$Report"
    exit 0
}

Write-Host "STATUS=HOLD_ROTATIONAL_DRAWING_NO_USABLE_ARTIFACT"
Write-Host "NATIVE_RC=$nativeRc"
Write-Host "REPORT=$Report"
exit 3
