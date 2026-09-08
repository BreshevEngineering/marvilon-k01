param(
  [Parameter(Mandatory=$true)][string]$ProvenancePath,
  [string]$RepoRoot=""
)
$ErrorActionPreference='Stop'
if([string]::IsNullOrWhiteSpace($RepoRoot)){
  $RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
function Abs([string]$p){if([IO.Path]::IsPathRooted($p)){return $p};return (Join-Path $RepoRoot $p)}
function Sha([string]$p){if(-not(Test-Path -LiteralPath $p -PathType Leaf)){return ''};return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}

$p=Abs $ProvenancePath
$j=Get-Content -LiteralPath $p -Raw -Encoding UTF8|ConvertFrom-Json
$checks=@()

$ev=Abs ([string]$j.evidence_path)
$actual=Sha $ev
$checks += [pscustomobject]@{kind='evidence';path=$j.evidence_path;recorded=$j.evidence_sha256;actual=$actual;match=($actual -eq $j.evidence_sha256)}

$sp=Abs ([string]$j.tool.script_path)
$actualScript=Sha $sp
$checks += [pscustomobject]@{kind='tool_script';path=$j.tool.script_path;recorded=$j.tool.script_sha256;actual=$actualScript;match=($actualScript -eq $j.tool.script_sha256)}

foreach($i in @($j.inputs)){
  $ip=Abs ([string]$i.path)
  $a=Sha $ip
  $checks += [pscustomobject]@{kind='input';artifact_id=$i.artifact_id;path=$i.path;recorded=$i.sha256;actual=$a;match=($a -eq $i.sha256)}
}

$bad=@($checks|Where-Object{-not $_.match})
$r=[pscustomobject]@{
  schema='k01.provenance_check.v1'
  provenance_path=$ProvenancePath
  status=if($bad.Count -eq 0){'CURRENT'}else{'STALE'}
  mismatches=$bad
  checks=$checks
}
$r|ConvertTo-Json -Depth 20
if($bad.Count){exit 2}else{exit 0}
