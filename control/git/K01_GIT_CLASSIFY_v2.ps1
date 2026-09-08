param([string]$RepoRoot="")
& (Join-Path $PSScriptRoot "K01_GIT_CLASSIFY.ps1") -RepoRoot $RepoRoot
exit $LASTEXITCODE
