param([string]$RepoRoot="")
$ErrorActionPreference='Stop'
if([string]::IsNullOrWhiteSpace($RepoRoot)){$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path}
& (Join-Path $PSScriptRoot 'reducer.ps1') -RepoRoot $RepoRoot | Out-Null
$j=Get-Content (Join-Path $RepoRoot 'reports\control\K01_CURRENT_STATE.json') -Raw -Encoding UTF8|ConvertFrom-Json

Write-Host "K01 Requirements coverage"
Write-Host "  total    : $($j.requirements.total)"
Write-Host "  released : $($j.requirements.released)"
Write-Host "  blockers : $($j.requirements.blockers)"
Write-Host ""
$j.requirements.rows|Where-Object{$_.release_blocker}|ForEach-Object{
  Write-Host ("BLOCK "+$_.id+" | "+$_.title) -ForegroundColor Yellow
  Write-Host ("  "+$_.statement)
  Write-Host ("  verification: "+$_.verification_method)
}
