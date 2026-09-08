param(
  [Parameter(Mandatory=$true)][string]$EvidencePath,
  [Parameter(Mandatory=$true)][string]$EvidenceId,
  [Parameter(Mandatory=$true)][string[]]$InputPaths,
  [Parameter(Mandatory=$true)][string]$ToolName,
  [Parameter(Mandatory=$true)][string]$ToolVersion,
  [Parameter(Mandatory=$true)][string]$ScriptPath,
  [string]$RepoRoot=""
)
$ErrorActionPreference='Stop'

if([string]::IsNullOrWhiteSpace($RepoRoot)){
  $RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Abs([string]$p){
  if([IO.Path]::IsPathRooted($p)){return $p}
  return (Join-Path $RepoRoot $p)
}
function Sha([string]$p){
  if(-not(Test-Path -LiteralPath $p -PathType Leaf)){throw "Input/evidence file missing: $p"}
  return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Rel([string]$p){
  try{
    $u1=[Uri]((Get-Item -LiteralPath $RepoRoot).FullName.TrimEnd('\')+'\')
    $u2=[Uri](Get-Item -LiteralPath $p).FullName
    return [Uri]::UnescapeDataString($u1.MakeRelativeUri($u2).ToString()).Replace('/','\')
  }catch{return $p}
}

$ev=Abs $EvidencePath
$script=Abs $ScriptPath
$inputs=@()
$index=1
foreach($ip in $InputPaths){
  $a=Abs $ip
  $inputs += [pscustomobject]@{
    artifact_id=("INPUT-{0:D2}" -f $index)
    path=(Rel $a)
    sha256=(Sha $a)
  }
  $index++
}

$r=[pscustomobject]@{
  schema='k01.evidence_provenance.v1'
  evidence_id=$EvidenceId
  evidence_path=(Rel $ev)
  evidence_sha256=(Sha $ev)
  created=(Get-Date).ToString('o')
  tool=[pscustomobject]@{
    name=$ToolName
    version=$ToolVersion
    script_path=(Rel $script)
    script_sha256=(Sha $script)
  }
  inputs=$inputs
  stale_policy='STALE iff any recorded input SHA-256 or tool-script SHA-256 no longer matches current content.'
}

$out=$ev+'.provenance.json'
$r|ConvertTo-Json -Depth 20|Set-Content -LiteralPath $out -Encoding UTF8
Write-Host "Provenance registered: $out"
exit 0
