param([string]$RepoRoot="")
$ErrorActionPreference="Stop"
if([string]::IsNullOrWhiteSpace($RepoRoot)){$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path}

$specDir=Join-Path $RepoRoot "control\drawings\spec"
$outDir=Join-Path $RepoRoot "reports\drawings"
New-Item $outDir -ItemType Directory -Force|Out-Null

$rows=@()
$definitionErrors=@()
$releaseHolds=@()
$warnings=@()
$specFiles=@(Get-ChildItem $specDir -Filter "*DRAWING_INTENT*.json" -File)

function Has-AllowableVariation([string]$type,[string]$spec){
  if($type -in @('MATERIAL','DATUM')){return $true}
  if([string]::IsNullOrWhiteSpace($spec)){return $false}
  $patterns=@(
    '±',
    '\+\s*\d+(\.\d+)?\s*/\s*0',
    '\+\s*\d+(\.\d+)?\s*/\s*-\s*\d+',
    '\b[HhGgFfJjKkMmNnPpRrSsTtUuXxZz][4-9]\b',
    '\b6[HhGg]\b',
    '\bBASIC\b',
    '\bposition\b',
    '\bflatness\b',
    '\bperpendicularity\b',
    '\bparallelism\b',
    '\brunout\b',
    '\bprofile\b',
    '\bREF\b',
    '\breference\b',
    '\d+\.\d+\s*…\s*\d+\.\d+',
    '\d+\.\d+\s*\.\.\.\s*\d+\.\d+'
  )
  foreach($p in $patterns){if($spec -match $p){return $true}}
  return $false
}

function Is-Provisional([string]$text){
  if([string]::IsNullOrWhiteSpace($text)){return $false}
  return ($text -match '(?i)\bOPEN\b|\bSTUDY\b|CANDIDATE|NOT APPROVED|TO BE TAKEN|TO BE DEFINED|TBD|TBC|PROVISIONAL|PRELIMINARY')
}

foreach($f in $specFiles){
  try{$j=Get-Content $f.FullName -Raw -Encoding UTF8|ConvertFrom-Json}
  catch{$definitionErrors+="$($f.Name): JSON parse failed: $($_.Exception.Message)";continue}

  foreach($k in @('drawing_no','part_no','description','status','nominal_geometry_authority','projection','sheet','units')){
    if([string]::IsNullOrWhiteSpace([string]$j.$k)){$definitionErrors+="$($f.Name): missing top-level field '$k'"}
  }
  if(@($j.views).Count -lt 2){$definitionErrors+="$($f.Name): fewer than two controlled drawing views"}
  if(@($j.characteristics).Count -eq 0){$definitionErrors+="$($f.Name): no release characteristics"}

  $drawingReleaseReady=([string]$j.status -eq 'RELEASE_READY')
  if(-not $drawingReleaseReady){
    $releaseHolds+="$($j.drawing_no): drawing-intent status is '$($j.status)', not RELEASE_READY."
  }

  $ids=@{}
  foreach($c in @($j.characteristics)){
    $defStatus='PASS'
    $defIssues=@()
    $charHolds=@()

    if([string]::IsNullOrWhiteSpace([string]$c.id)){$defStatus='FAIL';$defIssues+='missing characteristic id'}
    elseif($ids.ContainsKey([string]$c.id)){$defStatus='FAIL';$defIssues+='duplicate characteristic id'}
    else{$ids[[string]$c.id]=$true}

    foreach($k in @('feature','type','spec','source','view','inspection')){
      if([string]::IsNullOrWhiteSpace([string]$c.$k)){$defStatus='FAIL';$defIssues+="missing $k"}
    }

    $joined="$($c.spec) $($c.source)"
    if(Is-Provisional $joined){$charHolds+="provisional/open wording in release characteristic"}

    if(-not (Has-AllowableVariation ([string]$c.type) ([string]$c.spec))){
      if([string]$c.type -in @('SIZE','FIT','THREAD','THREAD_GDT','HOLE_GDT','HOLE_PATTERN','GD&T')){
        $charHolds+="allowable variation / fit / GD&T is not explicit"
      } else {
        $warnings+="$($c.id): verify that allowable variation is explicit for type '$($c.type)': $($c.spec)"
      }
    }

    if([string]$c.inspection -match '(?i)\bOPEN\b|TBD|TO BE'){
      $charHolds+="inspection method is provisional"
    }

    if($defStatus -eq 'FAIL'){$definitionErrors+="$($j.drawing_no)/$($c.id): $($defIssues -join '; ')"}
    foreach($x in $charHolds){$releaseHolds+="$($j.drawing_no)/$($c.id): $x — $($c.spec)"}

    $rows+=[pscustomobject]@{
      drawing=$j.drawing_no
      part=$j.part_no
      characteristic=$c.id
      feature=$c.feature
      type=$c.type
      definition_status=$defStatus
      release_status=if($charHolds.Count -eq 0 -and $drawingReleaseReady){'READY'}else{'HOLD'}
      issues=(@($defIssues)+@($charHolds) -join '; ')
      specification=$c.spec
      inspection=$c.inspection
    }
  }
}

if($specFiles.Count -eq 0){$definitionErrors+='No drawing-intent specifications found.'}

$definitionStatus=if($definitionErrors.Count -eq 0){'PASS_SEMANTIC_DEFINITION'}else{'HOLD_DEFINITION_ERROR'}
$releaseStatus=if($definitionErrors.Count -eq 0 -and $releaseHolds.Count -eq 0){'PASS_RELEASE_SEMANTIC'}else{'HOLD_RELEASE_OPEN_CHARACTERISTICS'}

$report=[pscustomobject]@{
  schema='k01_drawing_intent_lint_v2'
  created=(Get-Date).ToString('o')
  definition_status=$definitionStatus
  status=$releaseStatus
  spec_count=$specFiles.Count
  characteristic_count=$rows.Count
  definition_errors=$definitionErrors
  release_holds=$releaseHolds
  warnings=$warnings
  rows=$rows
  release_rule='PASS_RELEASE_SEMANTIC requires a structurally valid drawing-intent definition, RELEASE_READY status for every drawing, and no OPEN/STUDY/CANDIDATE/unbounded critical characteristic.'
  note='Semantic release is still not visual drawing approval. Native SLDDRW/PDF must also pass controlled visual review and PDF hash binding.'
}
$report|ConvertTo-Json -Depth 20|Set-Content (Join-Path $outDir 'K01_DRAWING_INTENT_LINT_CURRENT.json') -Encoding UTF8

Write-Host "Drawing intent lint v2"
Write-Host "Definition : $definitionStatus"
Write-Host "Release    : $releaseStatus"
Write-Host "Specs      : $($specFiles.Count)"
Write-Host "Chars      : $($rows.Count)"
Write-Host "Def errors : $($definitionErrors.Count)"
Write-Host "Rel holds  : $($releaseHolds.Count)"
Write-Host "Warnings   : $($warnings.Count)"
if($definitionErrors.Count){
  $definitionErrors|ForEach-Object{Write-Host "DEFINITION ERROR: $_" -ForegroundColor Red}
  exit 2
}
if($releaseHolds.Count){
  Write-Host ""
  Write-Host "Engineering release HOLD is valid tool output; the linter itself executed successfully." -ForegroundColor Yellow
  $releaseHolds|ForEach-Object{Write-Host "RELEASE HOLD: $_" -ForegroundColor Yellow}
}
exit 0
