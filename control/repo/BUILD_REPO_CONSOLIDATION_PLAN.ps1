param([string]$RepoRoot="")
$ErrorActionPreference="Stop"
if([string]::IsNullOrWhiteSpace($RepoRoot)){$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path}
$src=Join-Path $RepoRoot "reports\git\K01_GIT_CLASSIFICATION_CURRENT.json"
if(-not(Test-Path -LiteralPath $src -PathType Leaf)){throw "Missing Git classification: $src"}
$j=Get-Content $src -Raw -Encoding UTF8|ConvertFrom-Json
$legacy=@()
$active=@()
foreach($x in @($j.source_control_candidate)){
 $p=[string]$x.path
 if($p -match '(_v[0-9]+|V[0-9]+|HOTFIX|PATCH_NOTES|STATIC_SANITY|00_INSTALL_MEDTAS_v|K01_Command_Center_v|cc_server_v)'){
   $legacy += $p
 } else {
   $active += $p
 }
}
$plan=[pscustomobject]@{
 schema="k01_repo_consolidation_plan_v1"
 created=(Get-Date).ToString("o")
 status="PLAN_ONLY_NO_FILE_MOVES"
 generated_local_count=@($j.generated_local).Count
 generated_local_action="Add stable ignore rules for bin/obj/live/current generated outputs; do not commit generated executables/DLLs."
 legacy_versioned_candidates=$legacy
 active_source_candidates=$active
 review_required=@($j.review_required|ForEach-Object{$_.path})
 execution_policy="Do not bulk git add. After T05/T07, move superseded MEDTAS/API source to controlled history/archive, keep stable runtime files, then create one reviewed checkpoint commit."
}
$out=Join-Path $RepoRoot "reports\git\K01_REPO_CONSOLIDATION_PLAN_CURRENT.json"
$plan|ConvertTo-Json -Depth 30|Set-Content -LiteralPath $out -Encoding UTF8
Write-Host "PLAN ONLY. No files moved/deleted/staged."
Write-Host "Generated local: $($plan.generated_local_count)"
Write-Host "Legacy/versioned candidates: $($legacy.Count)"
Write-Host "Active source candidates: $($active.Count)"
Write-Host "Review required: $(@($plan.review_required).Count)"
Write-Host "Report: $out"
