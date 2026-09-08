param([string]$RepoRoot="")
$ErrorActionPreference='Stop'

if([string]::IsNullOrWhiteSpace($RepoRoot)){
    $RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function P([string]$r){ Join-Path $RepoRoot $r }

function J([string]$r){
    $p=P $r
    if(-not(Test-Path -LiteralPath $p -PathType Leaf)){ return $null }
    try { return (Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json) }
    catch { return $null }
}

function IsPass($x){
    if($null -eq $x){ return $false }
    $s=[string]$x.status
    return ($s -eq 'PASS' -or $s.StartsWith('PASS_') -or $s.Contains('CONFIRMED'))
}

function IsTaskPass([string]$s){
    if([string]::IsNullOrWhiteSpace($s)){ return $false }
    return ($s -eq 'PASS' -or $s.StartsWith('PASS_'))
}

function NewTask($id,$name,$status,$why,$action,$manual,$depends){
    [pscustomobject]@{
        id=$id; name=$name; status=$status; why=$why; action=$action;
        manual=$manual; depends_on=@($depends); ready=$false
    }
}

$build   = J 'reports\cad\current\K01_GATE04D_C2R1_TYPED_BUILD.json'
$verify  = J 'reports\cad\current\K01_GATE04D_C2R1_VERIFY.json'
$int     = J 'reports\cad\current\K01_GATE04D_C2R1_INTERFERENCE.json'
$p006    = J 'reports\cad\current\K01_GATE04E_P006_SERVICE_BUILD.json'
$p006Verify = J 'reports\cad\current\K01_GATE04E_P006_SERVICE_VERIFY.json'
$seal    = J 'reports\qualification\K01_J2_SEAL_QUALIFICATION_CURRENT.json'
$torque  = J 'reports\qualification\K01_M2P5_TORQUE_CLAMP_CURRENT.json'
$local   = J 'reports\analysis\current\K01_J2_LOCAL_CONTACT_RELEASE.json'
$service = J 'reports\qualification\K01_J2_SERVICE_CYCLES_CURRENT.json'
$static  = J 'reports\simulation\K01_P007_STATIC_C2R1_RELEASE.json'
$buck    = J 'reports\simulation\K01_P007_BUCKLING_C2R1_RELEASE.json'
$proj    = J 'reports\bom\K01_BOM_PROPERTY_PROJECTION_CURRENT.json'
$bom     = J 'reports\bom\K01_BOM_RECONCILIATION_study_c2r1.json'
$dv3     = J 'reports\cad\current\K01_GATE04D_C2R1_TYPED_DRAWINGS_V3.json'
$lint    = J 'reports\drawings\K01_DRAWING_INTENT_LINT_CURRENT.json'
$visual  = J 'reports\drawings\K01_DRAWING_VISUAL_APPROVAL_CURRENT.json'
$femmInstall = J 'reports\femm\K01_FEMM_INSTALL_CURRENT.json'
$femm    = J 'reports\femm\K01_FINAL_FEMM_RELEASE.json'
$bench   = J 'reports\test\K01_ACTUATION_BENCH_ACCEPTANCE.json'
$swLive  = J 'reports\cad\live\K01_SOLIDWORKS_LIVE_STATE.json'
$githubRemote = J 'reports\git\K01_GITHUB_REMOTE_HEALTH_CURRENT.json'

$buildPass   = (IsPass $build)
$verifyPass  = (IsPass $verify)
$intPass     = (IsPass $int)
$p006Pass    = (IsPass $p006)
$p006VerifyPass = (IsPass $p006Verify)
$p006CadPass = ($p006Pass -and $p006VerifyPass)
$sealPass    = (IsPass $seal)
$torquePass  = (IsPass $torque)
$localPass   = (IsPass $local)
$servicePass = (IsPass $service)
$staticPass  = (IsPass $static)
$buckPass    = (IsPass $buck)
$femmPass    = (IsPass $femm)
$benchPass   = (IsPass $bench)
$visualPass  = (IsPass $visual)

$matePass=$false
if($verify -and ($verify.PSObject.Properties.Name -contains 'active_mate_errors')){
    $matePass=([int]$verify.active_mate_errors -eq 0)
}

$interferencePass=$false
if($int -and ($int.PSObject.Properties.Name -contains 'new_or_unclassified_count')){
    $interferencePass=([int]$int.new_or_unclassified_count -eq 0)
}

$cadPass=($buildPass -and $verifyPass -and $intPass -and $matePass -and $interferencePass)

$projectionPass=$false
if($proj -and ([string]$proj.status -eq 'PASS_APPLY') -and $bom){
    if($bom.PSObject.Properties.Name -contains 'metadata_projection_required'){
        $projectionPass=([int]$bom.metadata_projection_required -eq 0)
    }
}

$drawingNativePass=$false
if($dv3){ $drawingNativePass=([string]$dv3.status -like 'PASS*') }
$drawingSemanticPass=$false
if($lint){ $drawingSemanticPass=([string]$lint.status -eq 'PASS_RELEASE_SEMANTIC') }
$drawingReleasePass=($drawingNativePass -and $drawingSemanticPass -and $visualPass)
$femmBenchPass=($femmPass -and $benchPass)
$localJointPass=($torquePass -and $localPass)
$structuralPass=($staticPass -and $buckPass)

$drawingSpecs=@(
    (J 'control\drawings\spec\K01-D-003_P003_DRAWING_INTENT_v1.json'),
    (J 'control\drawings\spec\K01-D-006_P007_DRAWING_INTENT_v1.json'),
    (J 'control\drawings\spec\K01-D-005_P006_DRAWING_INTENT_v1.json')
)

$drawAction='RUN_DRAW_V3'
if($drawingNativePass){
    if($null -eq $lint){ $drawAction='RUN_DRAW_LINT' }
    elseif(-not $drawingSemanticPass){ $drawAction='OPEN_WP_T09' }
    elseif(-not $visualPass){ $drawAction='RUN_DRAW_VISUAL' }
    else { $drawAction='' }
}

$bomAction='RUN_BOM_DRY'
if($proj -and ([string]$proj.status -eq 'PASS_DRY_RUN')){ $bomAction='RUN_BOM_APPLY' }

$tasks=@()
$tasks += NewTask 'T02' 'C2R1 geometry / assembly / interference' $(if($cadPass){'PASS'}else{'HOLD'}) 'Native C2R1 candidate geometry, J2 mate architecture and hard-interference gate.' 'RUN_C2R1_ALL' $false @()
$tasks += NewTask 'T03' 'Tolerance chain + P006 service drive' $(if($p006CadPass){'PASS_CAD / MATERIAL_RELEASE_OPEN'}else{'ENGINEERING_PASS / CAD_OPEN'}) 'H9/h9 and fastener-position stacks are defined; T03 passes its CAD scope after the P006 candidate and full C2R1+P006 assembly verification pass. P006 production material remains a separate product-release hold.' 'RUN_P006_SERVICE' $false @('T02')
$tasks += NewTask 'T04' 'Seal media + compound + compression/leak qualification' $(if($sealPass){'PASS'}else{'HOLD_QUALIFICATION'}) 'FKM 75A is the preferred bounded-BOF candidate with FFKM fallback; local temperature/media/compound/force/leak evidence remains.' 'OPEN_WP_T04' $true @('T02')
$tasks += NewTask 'T05' 'M2.5 preload / local flange / torque process' $(if($localJointPass){'PASS'}else{'SCREEN_PASS / QUALIFICATION_OPEN'}) '200–300 N/screw study window passes thread/contact screening. Release still requires actual seal load, torque–clamp calibration and local contact evidence.' 'OPEN_WP_T05' $true @('T04')
$tasks += NewTask 'T06' 'Thermal preload / galling / service cycles' $(if($servicePass){'PASS'}else{'HOLD_QUALIFICATION'}) 'Matched stainless CTE is favorable; released finish/lubrication and repeated-service qualification remain.' 'OPEN_WP_T06' $true @('T05')
$tasks += NewTask 'T07' 'P007 final static + buckling refresh' $(if($structuralPass){'PASS'}else{'RUN_REQUIRED'}) 'Historical results remain background evidence only; final C2R1 geometry/preload needs one release refresh.' 'OPEN_WP_T07' $true @('T05','T06')
$tasks += NewTask 'T08' 'BOM property projection / normalization' $(if($projectionPass){'PASS'}else{'HOLD_METADATA'}) 'Project controlled identity/text properties into native files, then rerun BOM reconciliation. OPEN materials remain OPEN.' $bomAction $false @('T02')
$tasks += NewTask 'T09' 'TPD production drawings' $(if($drawingReleasePass){'PASS'}else{'HOLD_DRAWING_RELEASE'}) 'Release needs native V3 + release-semantic lint + visual approval bound to PDF hashes. A generated PDF alone is not release evidence.' $drawAction $false @('T02')
$tasks += NewTask 'T10' 'P015/B001 freeze -> FEMM -> bench' $(if($femmBenchPass){'PASS'}else{'HOLD_INPUT_OR_TEST'}) 'Final electromagnetic release is fail-closed until production magnet/coil inputs, FEMM and bench evidence exist.' 'OPEN_WP_T10' $true @('T07')
$tasks += NewTask 'T11' 'Atomic P003/P007 promotion' 'HOLD' 'Promotion remains blocked until the production-release dependency set closes and the technical filter contains no hard holds.' '' $true @('T03','T04','T05','T06','T07','T08','T09','T10')

$statusById=@{}
foreach($t in $tasks){ $statusById[$t.id]=[string]$t.status }
foreach($t in $tasks){
    $depsReady=$true
    foreach($d in @($t.depends_on)){
        if(-not $statusById.ContainsKey($d)){ $depsReady=$false; break }
        if(-not(IsTaskPass ([string]$statusById[$d]))){ $depsReady=$false; break }
    }
    $t.ready=($depsReady -and -not(IsTaskPass ([string]$t.status)))
}

$readyNow=@($tasks | Where-Object{$_.ready})
$nextTask=$readyNow | Select-Object -First 1
if($null -eq $nextTask){ $nextTask=$tasks | Where-Object{-not(IsTaskPass ([string]$_.status))} | Select-Object -First 1 }

$state=[pscustomobject]@{
    schema='k01_state_v8_1'; generated=(Get-Date).ToString('o'); active_design='Gate04D-C2R1';
    design_geometry='FROZEN'; production_release='HOLD'; tasks=$tasks; next_task=$nextTask; ready_now=$readyNow;
    release=(J 'control\release\K01_J2_C2R1_PRODUCTION_RELEASE_PACKAGE_v1.json');
    technical_filter=(J 'control\technical_filter\K01_J2_C2R1_TECHNICAL_FILTER_v1.json');
    digital_thread=(J 'control\digital_thread\K01_MEDTAS_DIGITAL_THREAD_ARCHITECTURE_v2.json');
    solidworks_live=$swLive
    femm_install=$femmInstall
    github_remote=$githubRemote;
    workpacks=[pscustomobject]@{
        T03=(J 'control\workpacks\K01_T03_PILOT_TOOL_WORKPACKAGE_v2.json');
        T04=(J 'control\workpacks\K01_T04_SEAL_PRELOAD_WORKPACKAGE_v1.json');
        T04_MEDIA=(J 'control\workpacks\K01_T04_MEDIA_ENVELOPE_v1.json');
        T05=(J 'control\workpacks\K01_T05_J2_CLAMP_STRENGTH_WORKPACKAGE_v1.json');
        T06=(J 'control\workpacks\K01_T06_THERMAL_GALLING_SERVICE_WORKPACKAGE_v1.json');
        T07=(J 'control\workpacks\K01_T07_P007_STRUCTURAL_REFRESH_v1.json');
        T08=(J 'control\workpacks\K01_T08_BOM_PROPERTY_PROJECTION_v1.json');
        T09=(J 'control\workpacks\K01_T09_DRAWING_TPD_RELEASE_v1.json');
        T10=(J 'control\workpacks\K01_T10_FEMM_BENCH_RELEASE_v1.json')
    };
    drawing_standard=(J 'control\drawings\K01_TPD_DRAWING_ASSURANCE_STANDARD_v1.json');
    drawing_specs=$drawingSpecs;
    evidence=[pscustomobject]@{
        build=$build;verify=$verify;interference=$int;p006=$p006;seal=$seal;torque=$torque;local=$local;service=$service;
        static=$static;buckling=$buck;property_projection=$proj;bom=$bom;drawing_v3=$dv3;drawing_lint=$lint;
        drawing_visual=$visual;femm=$femm;bench=$bench;solidworks_live=$swLive
        github_remote=$githubRemote
    }
}

$out=P 'control\state\K01_STATE_CURRENT_v8.json'
$state | ConvertTo-Json -Depth 50 | Set-Content -LiteralPath $out -Encoding UTF8

$ledger=P 'control\state\K01_EVENT_LEDGER_v8.jsonl'
$prev=J 'control\state\K01_TASK_STATUS_PREVIOUS_v8.json'
$old=@{}
if($prev){ foreach($x in @($prev)){ $old[[string]$x.id]=[string]$x.status } }
$now=(Get-Date).ToString('o')
foreach($x in $tasks){
    $before='<NEW>'
    if($old.ContainsKey([string]$x.id)){ $before=[string]$old[[string]$x.id] }
    if($before -ne [string]$x.status){
        [pscustomobject]@{schema='k01_event_v1';time=$now;type='TASK_STATUS_CHANGED';task_id=$x.id;from=$before;to=$x.status;active_design='Gate04D-C2R1'} |
            ConvertTo-Json -Compress | Add-Content -LiteralPath $ledger -Encoding UTF8
    }
}
$tasks | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (P 'control\state\K01_TASK_STATUS_PREVIOUS_v8.json') -Encoding UTF8
$state | ConvertTo-Json -Depth 50
