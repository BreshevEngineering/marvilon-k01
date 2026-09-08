param([string]$RepoRoot="")
$ErrorActionPreference='Stop'
if([string]::IsNullOrWhiteSpace($RepoRoot)){$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path}
$out=Join-Path $RepoRoot 'reports\git\K01_GITHUB_REMOTE_HEALTH_CURRENT.json'
New-Item ([IO.Path]::GetDirectoryName($out)) -ItemType Directory -Force|Out-Null

$origin=''
try{$origin=(& git -C $RepoRoot remote get-url origin 2>&1|Out-String).Trim()}catch{}
$branch=''
try{$branch=(& git -C $RepoRoot branch --show-current 2>&1|Out-String).Trim()}catch{}
$remoteOk=$false;$remoteText=''
try{
 $remoteText=(& git -C $RepoRoot ls-remote --exit-code origin HEAD 2>&1|Out-String).Trim()
 if($LASTEXITCODE -eq 0){$remoteOk=$true}
}catch{$remoteText=$_.Exception.Message}

$status=if($remoteOk){'PASS_REMOTE_REACHABLE'}else{'HOLD_REMOTE_UNREACHABLE_OR_AUTH'}
$r=[pscustomobject]@{
 schema='k01_github_remote_health_v1'
 created=(Get-Date).ToString('o')
 status=$status
 origin=$origin
 branch=$branch
 remote_head=$remoteText
 read_only=$true
 note='Uses git remote get-url and git ls-remote only. No fetch, pull, push, stage or commit is performed.'
}
$r|ConvertTo-Json -Depth 10|Set-Content $out -Encoding UTF8
Write-Host "GitHub remote: $status"
Write-Host "Origin: $origin"
if($remoteText){Write-Host $remoteText}
Write-Host "Report: $out"
if($remoteOk){exit 0}else{exit 2}
