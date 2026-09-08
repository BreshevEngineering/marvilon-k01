param([string]$RepoRoot="")
$ErrorActionPreference="Stop"
if([string]::IsNullOrWhiteSpace($RepoRoot)){$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path}
$outDir=Join-Path $RepoRoot "reports\git";New-Item $outDir -ItemType Directory -Force|Out-Null
$out=Join-Path $outDir "K01_GIT_CLASSIFICATION_CURRENT.json"

function Category($path){
    $p=$path.Replace("\","/")
    if($p -match '(^|/)(bin|obj|__pycache__|\.pytest_cache)(/|$)'){return "GENERATED_LOCAL"}
    if($p -match '\.(SLDPRT|SLDASM|SLDDRW|STEP|STP|IGES|IGS)$'){return "CAD_OUTSIDE_GIT"}
    if($p -match '^handoff/current/.*\.zip$'){return "GENERATED_LOCAL"}
    if($p -match '^reports/.+_\d{8}_\d{6}\.log$'){return "EVIDENCE_LOG_LOCAL"}
    if($p -match '^reports/.+/(current/)?[^/]+\.json$'){return "CURRENT_STRUCTURED_EVIDENCE"}
    if($p -match '^(cad_api|control|master|params|scripts|spec|tests|tools|docs)/'){return "SOURCE_CONTROL_CANDIDATE"}
    if($p -match '^bom/.*\.(json|csv)$'){return "SOURCE_CONTROL_CANDIDATE"}
    if($p -match '^(\.github|\.githooks)/'){return "SOURCE_CONTROL_CANDIDATE"}
    if($p -match '^\.(gitignore|gitattributes)$'){return "SOURCE_CONTROL_CANDIDATE"}
    return "REVIEW_REQUIRED"
}
$lines=& git -C $RepoRoot status --porcelain=v1
$items=@()
foreach($line in @($lines)){
    if([string]::IsNullOrWhiteSpace($line)){continue}
    $xy=$line.Substring(0,2)
    $path=$line.Substring(3)
    if($path -match ' -> '){$path=($path -split ' -> ')[-1]}
    $items+=[pscustomobject]@{xy=$xy;path=$path;category=Category $path}
}
$groups=@{}
foreach($i in $items){if(-not $groups.ContainsKey($i.category)){$groups[$i.category]=0};$groups[$i.category]++}
$report=[pscustomobject]@{
 schema="k01_git_classification_v1"
 created=(Get-Date).ToString("o")
 branch=(& git -C $RepoRoot branch --show-current|Out-String).Trim()
 last_commit=(& git -C $RepoRoot log -1 --format="%H|%cI|%s"|Out-String).Trim()
 dirty_count=$items.Count
 untracked_count=@($items|Where-Object{$_.xy -eq "??"}).Count
 categories=$groups
 checkpoint_readiness=if(@($items|Where-Object{$_.category -eq "REVIEW_REQUIRED"}).Count -eq 0){"CLASSIFIED_NOT_COMMITTED"}else{"HOLD_UNCLASSIFIED_PATHS"}
 items=$items
 policy=@(
   "Do not commit native SOLIDWORKS CAD through normal Git.",
   "Commit source/control/master/spec/test code and selected canonical structured evidence after engineering gate coherence.",
   "Keep timestamp logs, build binaries and AI handoff ZIPs local or in an artifact store.",
   "REVIEW_REQUIRED paths must be explicitly classified before a checkpoint."
 )
}
$report|ConvertTo-Json -Depth 12|Set-Content $out -Encoding UTF8
Write-Host "Git classification: dirty=$($report.dirty_count) untracked=$($report.untracked_count) readiness=$($report.checkpoint_readiness)"
foreach($k in $groups.Keys|Sort-Object){Write-Host ("  "+$k+" = "+$groups[$k])}
Write-Host "Report: $out"
