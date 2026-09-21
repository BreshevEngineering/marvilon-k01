$ErrorActionPreference = "Stop"
$Repo = "D:\BreshevEngineering\marvilon-k01"
if ($args.Count -lt 1) {
    Write-Host "Usage: RUN_K01_DRAWING_BUILD_API.cmd <build-job.json>"
    exit 2
}
$JobPath=(Resolve-Path -LiteralPath $args[0]).Path
$Job=Get-Content -LiteralPath $JobPath -Raw | ConvertFrom-Json

Write-Host "=== K01 DRAWING BUILD API V1 ==="
Write-Host "JOB=$JobPath"
Write-Host "MODE=STABLE FACADE OVER REGISTERED BUILD ADAPTER"

$RegistryPath = Join-Path $Repo "control\api\K01_DRAWING_BUILD_ADAPTER_REGISTRY_CURRENT.json"
if (!(Test-Path -LiteralPath $RegistryPath)) { throw "BUILD_ADAPTER_REGISTRY_MISSING: $RegistryPath" }
if (-not $Job.adapter_id) { throw "BUILD_JOB_MISSING_adapter_id" }
if ($Job.adapter_launcher) { throw "BUILD_JOB_PROHIBITED_adapter_launcher__USE_adapter_id" }

$Registry = Get-Content -LiteralPath $RegistryPath -Raw | ConvertFrom-Json
$matches = @($Registry.adapters | Where-Object { [string]$_.id -eq [string]$Job.adapter_id })
if ($matches.Count -ne 1) { throw "BUILD_ADAPTER_RESOLUTION_COUNT=$($matches.Count); expected exactly 1 for adapter_id=$($Job.adapter_id)" }
$Adapter = $matches[0]
if ([string]$Adapter.state -ne "EXISTING_ADAPTER") { throw "BUILD_ADAPTER_NOT_APPROVED: id=$($Adapter.id) state=$($Adapter.state)" }
if (-not $Adapter.launcher) { throw "BUILD_ADAPTER_LAUNCHER_UNDECLARED: id=$($Adapter.id)" }

$launcher=Join-Path $Repo ([string]$Adapter.launcher)
if (!(Test-Path -LiteralPath $launcher)) { throw "BUILD_ADAPTER_LAUNCHER_MISSING: $launcher" }
Write-Host "ADAPTER_ID=$($Adapter.id)"
Write-Host "ADAPTER_STATE=$($Adapter.state)"
Write-Host "ADAPTER_LAUNCHER=$launcher"

if ($Job.source_model) {
    $model=[string]$Job.source_model
    if (!(Test-Path -LiteralPath $model)) { throw "SOURCE_MODEL_MISSING: $model" }
    $shaBefore=(Get-FileHash -LiteralPath $model -Algorithm SHA256).Hash.ToLowerInvariant()
}

& $launcher
$rc=$LASTEXITCODE
if ($rc -ne 0) {
    Write-Host "STATUS=HOLD_DRAWING_BUILD_API"
    Write-Host "ADAPTER_RC=$rc"
    exit $rc
}

if ($Job.expected_output) {
    $out=[string]$Job.expected_output
    if (!(Test-Path -LiteralPath $out)) { throw "EXPECTED_OUTPUT_MISSING: $out" }
}

if ($Job.source_model) {
    $shaAfter=(Get-FileHash -LiteralPath $model -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($shaBefore -ne $shaAfter) { throw "SOURCE_MODEL_INVARIANCE_FAILED" }
}

Write-Host "STATUS=PASS_DRAWING_BUILD_ADAPTER_VIA_REGISTRY"
Write-Host "NEXT=Run semantic QA, then use DRAWING REFINE API for existing-object cleanup."
exit 0
