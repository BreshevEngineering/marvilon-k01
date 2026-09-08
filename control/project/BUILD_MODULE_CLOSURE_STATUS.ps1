param([string]$RepoRoot="")
$ErrorActionPreference="Stop"
if([string]::IsNullOrWhiteSpace($RepoRoot)){$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path}
function J([string]$r){$p=Join-Path $RepoRoot $r;if(Test-Path -LiteralPath $p -PathType Leaf){try{return Get-Content $p -Raw -Encoding UTF8|ConvertFrom-Json}catch{}};return $null}
$req=J "control\requirements\requirements.json";$t03=J "control\workpacks\K01_T03_CLOSEOUT_CURRENT.json";$t04=J "control\workpacks\K01_T04_SEAL_BASELINE_CURRENT.json";$t05=J "reports\calculations\K01_T05_CLAMP_SCREEN_CURRENT.json";$probe=J "reports\drawings\K01_P006_DRAWING_PROBE_CURRENT.json";$femm=J "reports\femm\FEMM_INSTALL_CURRENT.json"
$rows=@(
 [pscustomobject]@{id="MECH";status="PASS_CANDIDATE";next="No redesign unless evidence fails"},
 [pscustomobject]@{id="T03";status=if($t03.status -eq "PASS_T03"){"PASS"}else{"HOLD"};next="T06 service/galling"},
 [pscustomobject]@{id="T04";status=if($t04){"PASS_BASELINE"}else{"HOLD"};next="Supplier compound + leak test"},
 [pscustomobject]@{id="T05";status=if($t05){$t05.status}else{"OPEN"};next="Local FEA + torque/anti-galling"},
 [pscustomobject]@{id="T06";status="OPEN";next="Service cycle + galling process"},
 [pscustomobject]@{id="T07";status="OPEN";next="P007 Static +0.20 / Buckling -0.20 refresh"},
 [pscustomobject]@{id="DRAW";status=if($probe -and $probe.status -eq "PASS_READ_ONLY_PROBE"){"P006_COMPILER_INPUT_READY"}else{"P006_PROBE_OPEN"};next="Native P006 pilot -> P003/P007"},
 [pscustomobject]@{id="FEMM";status=if($femm.status -eq "PASS_FEMM_FOUND"){"SOLVER_PASS_INPUT_FREEZE_OPEN"}else{"HOLD"};next="P015/B001 freeze -> model/sweep"},
 [pscustomobject]@{id="BOM";status="STRUCTURE_EXISTS_METADATA_HOLDS";next="Project controlled metadata after remaining materials freeze"},
 [pscustomobject]@{id="REPO";status="DEFERRED_UNTIL_ENGINEERING_CHECKPOINT";next="Selective cleanup/commit after T05/T07"}
)
$out=[pscustomobject]@{schema="k01_module_closure_status_v2";created=(Get-Date).ToString("o");rows=$rows}
$p=Join-Path $RepoRoot "reports\control\K01_MODULE_CLOSURE_STATUS_CURRENT.json";New-Item ([IO.Path]::GetDirectoryName($p)) -ItemType Directory -Force|Out-Null;$out|ConvertTo-Json -Depth 20|Set-Content $p -Encoding UTF8
$rows|Format-Table -AutoSize
