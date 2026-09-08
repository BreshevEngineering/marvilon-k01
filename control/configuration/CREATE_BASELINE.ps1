param([string]$BaselineId,[string]$RepoRoot="")
$ErrorActionPreference='Stop'
if([string]::IsNullOrWhiteSpace($BaselineId)){throw 'BaselineId required'}
if([string]::IsNullOrWhiteSpace($RepoRoot)){$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path}
$state=Get-Content (Join-Path $RepoRoot 'reports\control\K01_CURRENT_STATE.json') -Raw -Encoding UTF8|ConvertFrom-Json
$block=@($state.requirements.rows|Where-Object{$_.release_blocker})
if($block.Count){throw "Baseline blocked by $($block.Count) unresolved requirement(s)."}

$artifactPaths=@(
 'control\requirements\requirements.json',
 'control\technical_filter\K01_J2_C2R1_TECHNICAL_FILTER_v1.json',
 'control\configuration\revision_policy.json',
 'control\bom\bom_policy.json'
)
$arts=@()
foreach($r in $artifactPaths){
 $p=Join-Path $RepoRoot $r;if(-not(Test-Path -LiteralPath $p -PathType Leaf)){throw "Baseline artifact missing: $r"}
 $arts+=[pscustomobject]@{artifact_id=$r;path=$r;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant();revision_state='RELEASED'}
}
$b=[pscustomobject]@{schema='k01.baseline.v1';baseline_id=$BaselineId;created=(Get-Date).ToString('o');artifacts=$arts}
$out=Join-Path $RepoRoot ("control\configuration\baselines\"+$BaselineId+".json")
New-Item ([IO.Path]::GetDirectoryName($out)) -ItemType Directory -Force|Out-Null
$b|ConvertTo-Json -Depth 20|Set-Content -LiteralPath $out -Encoding UTF8
Write-Host "Created baseline: $out"
