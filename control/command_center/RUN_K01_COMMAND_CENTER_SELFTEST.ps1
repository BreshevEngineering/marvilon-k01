param([string]$RepoRoot="")
$ErrorActionPreference='Stop'
$here=$PSScriptRoot
. (Join-Path $here 'cc_api_core_v8.ps1') -RepoRoot $RepoRoot

$out=Join-Path $script:MEDTAS_REPO 'reports\control\K01_COMMAND_CENTER_SELFTEST_CURRENT.json'
New-Item ([IO.Path]::GetDirectoryName($out)) -ItemType Directory -Force | Out-Null

$r=Test-MedtasApiCore
$r | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $out -Encoding UTF8

Write-Host "Command Center core self-test: $($r.status)"
foreach($x in $r.results){
    Write-Host ("  {0,-8} {1,-5} bytes={2} {3}" -f $x.subsystem,$x.status,$x.bytes,$x.error)
}
Write-Host "Report: $out"

if($r.failures -gt 0){exit 2}
exit 0
