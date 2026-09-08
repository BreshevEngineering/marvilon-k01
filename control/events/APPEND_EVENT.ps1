param(
  [Parameter(Mandatory=$true)][string]$Type,
  [Parameter(Mandatory=$true)][string]$Subject,
  [string]$PayloadJson='{}',
  [string]$RepoRoot=""
)
$ErrorActionPreference='Stop'
if([string]::IsNullOrWhiteSpace($RepoRoot)){$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path}
$ledger=Join-Path $RepoRoot 'control\events\engineering_events.jsonl'
New-Item ([IO.Path]::GetDirectoryName($ledger)) -ItemType Directory -Force|Out-Null

function ShaText([string]$s){
  $sha=[Security.Cryptography.SHA256]::Create()
  try{return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($s))).Replace('-','').ToLowerInvariant())}
  finally{$sha.Dispose()}
}

$last=$null;$seq=1;$prev=''
if(Test-Path -LiteralPath $ledger -PathType Leaf){
  $lines=@(Get-Content -LiteralPath $ledger -Encoding UTF8|Where-Object{-not [string]::IsNullOrWhiteSpace($_)})
  if($lines.Count){
    $last=$lines[-1]|ConvertFrom-Json
    $seq=[int]$last.seq+1
    $prev=[string]$last.event_hash
  }
}

$payload=$PayloadJson|ConvertFrom-Json
$base=[ordered]@{
  schema='k01.event.v2'
  seq=$seq
  timestamp=(Get-Date).ToString('o')
  type=$Type
  subject=$Subject
  payload=$payload
  previous_hash=$prev
}
$canonical=($base|ConvertTo-Json -Depth 30 -Compress)
$eventHash=ShaText ($prev+'|'+$canonical)

$event=[ordered]@{}
foreach($k in $base.Keys){$event[$k]=$base[$k]}
$event['event_hash']=$eventHash
($event|ConvertTo-Json -Depth 30 -Compress)|Add-Content -LiteralPath $ledger -Encoding UTF8
Write-Host "Appended event seq=$seq hash=$eventHash"
