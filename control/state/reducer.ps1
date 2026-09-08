param([string]$RepoRoot="")
$ErrorActionPreference='Stop'
if([string]::IsNullOrWhiteSpace($RepoRoot)){$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path}
. (Join-Path $PSScriptRoot 'reducer_core.ps1')

function ReadJson([string]$rel){
    $p=Join-Path $RepoRoot $rel
    if(-not(Test-Path -LiteralPath $p -PathType Leaf)){return $null}
    return Get-Content -LiteralPath $p -Raw -Encoding UTF8|ConvertFrom-Json
}

$requirements=ReadJson 'control\requirements\requirements.json'
$filter=ReadJson 'control\technical_filter\K01_J2_C2R1_TECHNICAL_FILTER_v1.json'
$bom=ReadJson 'reports\bom\K01_BOM_RECONCILIATION_study_c2r1.json'
$git=ReadJson 'reports\git\K01_GITHUB_REMOTE_HEALTH_CURRENT.json'
$femm=ReadJson 'reports\femm\K01_FEMM_INSTALL_CURRENT.json'

if($null -eq $requirements){throw 'requirements.json missing'}
if($null -eq $filter){throw 'technical filter missing'}

$coverage=@(Get-K01RequirementCoverage $requirements $filter)

$evidenceDefs=@(
    @{gate='interfaces_datums';path='reports\cad\current\K01_GATE04D_C2R1_VERIFY.json'},
    @{gate='assembly';path='reports\cad\current\K01_GATE04D_C2R1_VERIFY.json'},
    @{gate='change_impact';path='reports\cad\current\K01_GATE04D_C2R1_TYPED_BUILD.json'},
    @{gate='documentation_traceability';path='reports\cad\current\K01_GATE04D_C2R1_TYPED_BUILD.json'}
)
$fresh=@()
foreach($e in $evidenceDefs){
    $abs=Join-Path $RepoRoot $e.path
    if(Test-Path -LiteralPath $abs -PathType Leaf){
        $p=Get-K01ProvenanceStatus $abs $RepoRoot
        $fresh += [pscustomobject]@{gate=$e.gate;path=$e.path;status=[string]$p.status;details=$p}
    }else{
        $fresh += [pscustomobject]@{gate=$e.gate;path=$e.path;status='MISSING';details=$null}
    }
}

$gates=@()
foreach($g in @($filter.gates)){
    $gates += Resolve-K01GateState $g $coverage $fresh
}

$reqBlockers=@($coverage|Where-Object{$_.release_blocker})
$gateBlockers=@($gates|Where-Object{$_.status -match '^(HOLD|STALE|OPEN)'})
$unhashed=@($fresh|Where-Object{$_.status -eq 'UNHASHED'})

$currentAction='CLOSE_REQUIREMENTS'
if($reqBlockers.Count -eq 0){$currentAction='RUN_ENGINEERING_TASKS'}
if(@($coverage|Where-Object{$_.id -eq 'REQ-K01-MAT-P006-001' -and $_.release_blocker}).Count -gt 0){$currentAction='GATE04E_P006_AND_MATERIAL'}
if(@($coverage|Where-Object{$_.id -eq 'REQ-K01-ENV-DP-001' -and $_.release_blocker}).Count -gt 0){$currentAction='FREEZE_DIFFERENTIAL_PRESSURE_REQUIREMENT'}

$state=[pscustomobject]@{
    schema='k01.current_state.v1'
    generated=(Get-Date).ToString('o')
    requirements=[pscustomobject]@{
        total=$coverage.Count
        released=@($coverage|Where-Object{$_.requirement_status -eq 'RELEASED'}).Count
        blockers=$reqBlockers.Count
        rows=$coverage
    }
    gates=[pscustomobject]@{
        total=$gates.Count
        blockers=$gateBlockers.Count
        rows=$gates
    }
    provenance=[pscustomobject]@{
        tracked=$fresh.Count
        unhashed=$unhashed.Count
        rows=$fresh
    }
    bom=$bom
    github=$git
    femm=$femm
    current_action=$currentAction
}
$out=Join-Path $RepoRoot 'reports\control\K01_CURRENT_STATE.json'
New-Item ([IO.Path]::GetDirectoryName($out)) -ItemType Directory -Force|Out-Null
$state|ConvertTo-Json -Depth 50|Set-Content -LiteralPath $out -Encoding UTF8

# Hash-chained transition ledger. Previous state cache is not authority; it only detects transitions.
$previousPath=Join-Path $RepoRoot 'reports\control\K01_PREVIOUS_STATE.json'
$previous=$null
if(Test-Path -LiteralPath $previousPath -PathType Leaf){
    try{$previous=Get-Content -LiteralPath $previousPath -Raw -Encoding UTF8|ConvertFrom-Json}catch{}
}
$appendTool=Join-Path $RepoRoot 'control\events\APPEND_EVENT.ps1'
$verifyTool=Join-Path $RepoRoot 'control\events\VERIFY_LEDGER.ps1'
if(Test-Path -LiteralPath $appendTool -PathType Leaf){
    if(Test-Path -LiteralPath $verifyTool -PathType Leaf){
        & $verifyTool -RepoRoot $RepoRoot | Out-Null
        if($LASTEXITCODE -ne 0){throw 'Engineering event ledger hash chain is invalid; state transition recording blocked.'}
    }
    if($previous){
        $oldReq=@{};foreach($x in @($previous.requirements.rows)){$oldReq[[string]$x.id]=[string]$x.requirement_status}
        foreach($x in @($state.requirements.rows)){
            $before=if($oldReq.ContainsKey([string]$x.id)){$oldReq[[string]$x.id]}else{'<NEW>'}
            if($before -ne [string]$x.requirement_status){
                $payload=@{from=$before;to=[string]$x.requirement_status}|ConvertTo-Json -Compress
                & $appendTool -Type 'REQUIREMENT_STATUS_CHANGED' -Subject ([string]$x.id) -PayloadJson $payload -RepoRoot $RepoRoot | Out-Null
            }
        }
        $oldGate=@{};foreach($x in @($previous.gates.rows)){$oldGate[[string]$x.gate]=[string]$x.status}
        foreach($x in @($state.gates.rows)){
            $before=if($oldGate.ContainsKey([string]$x.gate)){$oldGate[[string]$x.gate]}else{'<NEW>'}
            if($before -ne [string]$x.status){
                $payload=@{from=$before;to=[string]$x.status}|ConvertTo-Json -Compress
                & $appendTool -Type 'GATE_STATUS_CHANGED' -Subject ([string]$x.gate) -PayloadJson $payload -RepoRoot $RepoRoot | Out-Null
            }
        }
    }
}
$state|ConvertTo-Json -Depth 50|Set-Content -LiteralPath $previousPath -Encoding UTF8

$state|ConvertTo-Json -Depth 50
