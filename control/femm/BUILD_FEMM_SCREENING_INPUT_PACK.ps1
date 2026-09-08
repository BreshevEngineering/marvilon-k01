param([string]$RepoRoot = "")
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$outRoot = Join-Path $RepoRoot "handoff\femm_current"
$stage = Join-Path $outRoot "K01_FEMM_SCREENING_INPUT"
$zip = Join-Path $outRoot "K01_FEMM_SCREENING_INPUT_CURRENT.zip"

New-Item $outRoot -ItemType Directory -Force | Out-Null
if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
New-Item $stage -ItemType Directory -Force | Out-Null

$wanted = @(
 "reports\femm\FEMM_INSTALL_CURRENT.json",
 "reports\cad\current\K01-P-015_Dual_Coil_Bobbin.json",
 "reports\cad\current\K01-B-001_Internal_SmCo_Magnet_D8x8_REFERENCE.json",
 "reports\cad\current\K01-P-007_Hermetic_Magnetic_Can.json",
 "reports\cad\current\K01-P-008_Internal_Magnetic_Follower.json",
 "reports\cad\current\K01_GATE04E_P006_SERVICE_BUILD.json",
 "reports\cad\current\K01_GATE04E_P006_SERVICE_VERIFY.json",
 "control\femm\K01_FEMM_SCREENING_PLAN_v1.json",
 "control\femm\K01_FEMM_SETUP_v1.json",
 "control\requirements\requirements.json"
)

$rows=@();$missing=@()
foreach($rel in $wanted){
  $src=Join-Path $RepoRoot $rel
  if(-not(Test-Path -LiteralPath $src -PathType Leaf)){
    $missing += $rel
    continue
  }
  $dst=Join-Path $stage $rel
  New-Item ([IO.Path]::GetDirectoryName($dst)) -ItemType Directory -Force|Out-Null
  Copy-Item -LiteralPath $src -Destination $dst -Force
  $rows += [pscustomobject]@{
    path=$rel
    sha256=(Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash.ToLowerInvariant()
    bytes=(Get-Item -LiteralPath $src).Length
  }
}

$manifest=[pscustomobject]@{
  schema="k01_femm_screening_input_manifest_v1"
  created=(Get-Date).ToString("o")
  status=if($missing.Count -eq 0){"PASS_INPUT_PACK_COMPLETE"}else{"HOLD_MISSING_INPUT_ARTIFACTS"}
  files=$rows
  missing=$missing
  release_note="This pack is for screening input preparation. Final FEMM remains blocked by actual B001 lot Br(T)/dimensions and released P015 winding/material data."
}
$manifest|ConvertTo-Json -Depth 20|Set-Content -LiteralPath (Join-Path $stage "MANIFEST.json") -Encoding UTF8
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zip -Force
Write-Host "FEMM input pack: $zip"
Write-Host "Status: $($manifest.status)"
if($missing.Count){Write-Host "Missing:"; $missing|ForEach-Object{Write-Host "  $_"}}
exit 0
