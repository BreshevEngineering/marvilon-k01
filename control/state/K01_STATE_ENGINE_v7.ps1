param(
    [string]$RepoRoot = ""
)
$ErrorActionPreference="Stop"
if([string]::IsNullOrWhiteSpace($RepoRoot)){
    $RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
function P($rel){Join-Path $RepoRoot $rel}
function ReadJ($rel){
    $p=P $rel
    if(-not(Test-Path -LiteralPath $p -PathType Leaf)){return $null}
    try{return Get-Content -LiteralPath $p -Raw -Encoding UTF8|ConvertFrom-Json}
    catch{return [pscustomobject]@{status="PARSE_ERROR";error=$_.Exception.Message;path=$p}}
}
function Sha($rel){
    $p=P $rel
    if(-not(Test-Path -LiteralPath $p -PathType Leaf)){return ""}
    return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash
}
function Info($rel,$role){
    $p=P $rel
    if(-not(Test-Path -LiteralPath $p -PathType Leaf)){
        return [pscustomobject]@{role=$role;path=$p;exists=$false;sha256="";modified="";status="MISSING"}
    }
    $j=ReadJ $rel
    $st="PRESENT"
    if($j -and $j.PSObject.Properties.Name -contains "status"){$st=[string]$j.status}
    return [pscustomobject]@{role=$role;path=$p;exists=$true;sha256=Sha $rel;modified=(Get-Item -LiteralPath $p).LastWriteTime.ToString("s");status=$st}
}
function IsPass($j){
    if($null -eq $j){return $false}
    $s=[string]$j.status
    return ($s -eq "PASS" -or $s.StartsWith("PASS_") -or $s.Contains("SCREEN_PASS") -or $s.Contains("CONFIRMED"))
}
function Task($id,$name,$status,$kind,$why,$action,$depends){
    [pscustomobject]@{id=$id;name=$name;status=$status;kind=$kind;why=$why;action=$action;depends_on=@($depends)}
}

$build=ReadJ "reports\cad\current\K01_GATE04D_C2R1_TYPED_BUILD.json"
$verify=ReadJ "reports\cad\current\K01_GATE04D_C2R1_VERIFY.json"
$int=ReadJ "reports\cad\current\K01_GATE04D_C2R1_INTERFERENCE.json"
$bomRaw=ReadJ "reports\bom\K01_BOM_AUDIT_study_c2r1.json"
$bomRec=ReadJ "reports\bom\K01_BOM_RECONCILIATION_study_c2r1.json"
$draw=ReadJ "reports\cad\current\K01_GATE04D_C2R1_TYPED_DRAWINGS_V2.json"
$drawQa=ReadJ "reports\cad\current\K01_DRAWING_QUALITY_P003_C2R1_v1.json"
$mech=ReadJ "reports\analysis\current\K01_J2_C2_MECHANICAL_SCREEN_v1.json"
$root=ReadJ "reports\analysis\current\K01_C2_PILOT_INTERFERENCE_ROOT_CAUSE_v1.json"

$r1Cad = if(IsPass $build -and IsPass $verify -and IsPass $int -and $verify.active_mate_errors -eq 0 -and $int.new_or_unclassified_count -eq 0){"PASS"}else{"OPEN"}
$bomStatus=if($bomRec){[string]$bomRec.status}else{"OPEN"}
$drawStatus=if($draw){if($draw.quality_status){[string]$draw.quality_status}else{[string]$draw.status}}elseif($drawQa){[string]$drawQa.status}else{"OPEN"}

$tasks=@()
$tasks+=Task "T01" "C2 failure root cause retained" $(if(IsPass $root){"PASS"}else{"HOLD"}) "EVIDENCE" "Preserve rejected C2 and exact P003/P006 collision proof." "OPEN_ROOTCAUSE" @()
$tasks+=Task "T02" "C2R1 native CAD + assembly + interference" $r1Cad "AUTOMATED" "Build, mate architecture and no-new-hard-interference are the geometry release gate." "RUN_C2R1_ALL" @("T01")
$tasks+=Task "T03" "Pilot tolerance chain + P006 service-tool envelope" "OPEN" "ENGINEERING" "Nominal 0.25 mm radial clearance is proven only at nominal geometry. Freeze P006 head tolerance, pilot-ID tolerance, worst-case clearance and tool access." "OPEN_EDR019" @("T02")
$tasks+=Task "T04" "Seal compound + clamp preload" "OPEN" "ENGINEERING_INPUT" "O-ring geometry exists, but compound/hardness/process-gas compatibility and compression force are needed before clamp preload is released." "OPEN_DOSSIER" @("T02")
$tasks+=Task "T05" "M2.5 joint + local flange/contact verification" "OPEN" "ANALYSIS" "Preliminary thread screen does not reject M2.5; final preload/friction/head-bearing/flange-separation verification remains." "OPEN_MECH" @("T04")
$tasks+=Task "T06" "Thermal preload + service/galling" "OPEN" "ENGINEERING" "Quantify preload drift, stainless galling/anti-seize policy, loosening and repeated service cycles." "OPEN_DOSSIER" @("T05")
$tasks+=Task "T07" "P007 static + buckling refresh" "STALE" "SOLVER" "Historical pressure/buckling screens must be refreshed once C2R1 mechanical geometry/preload is frozen." "" @("T05","T06")
$tasks+=Task "T08" "C2R1 BOM normalization / metadata projection" $bomStatus "AUTOMATED" "Assembly quantities are known; 13 metadata projections and 7 release blockers remain in the current reconciliation." "RUN_R1_BOM" @("T02")
$tasks+=Task "T09" "Production-capable drawing draft" $drawStatus "AUTOMATED" "A file existing is not enough. The drawing quality gate requires section, visible dimensions, title block and controlled callouts." "RUN_R1_DRAWINGS_V2" @("T02")
$tasks+=Task "T10" "Final FEMM impact/release model" "OPEN" "SOLVER" "Run after J2 mechanical freeze plus P015/B001 production data freeze." "" @("T05","T06","T07")
$tasks+=Task "T11" "Atomic P003/P007 promotion / release audit" "HOLD" "RELEASE" "Promote P003/P007 together only after all mandatory engineering gates and document/BOM controls pass." "" @("T03","T04","T05","T06","T07","T08","T09","T10")

# Derived EDS state: do not mutate the historical EDR record.
$eds=@(
 [pscustomobject]@{gate="functional_requirement";status=$(if($r1Cad -eq "PASS"){"PASS"}else{"HOLD"});basis="C2R1 preserves removable J2, P007 L35 and compact service architecture.";evidence=@("R1-BUILD","R1-VERIFY","R1-INT")},
 [pscustomobject]@{gate="architecture_integrity";status="PASS";basis="No permanent weld; pilot/face/clocking/clamp/seal functions remain separated.";evidence=@("CI-J2","EDR-005")},
 [pscustomobject]@{gate="interfaces_datums";status=$(if($r1Cad -eq "PASS"){"PASS"}else{"HOLD"});basis="R1 verify proves pilot concentric + axial face + M2.5 clocking and zero active mate errors.";evidence=@("R1-VERIFY")},
 [pscustomobject]@{gate="load_cases";status="HOLD";basis="Pressure case exists; preload/seal/service/thermal load envelope not fully bounded.";evidence=@("P007-static","DOS-J2-C2R1")},
 [pscustomobject]@{gate="static_strength_contact";status="HOLD";basis="M2.5 preliminary screen passes, but released preload and local flange/contact verification are open.";evidence=@("MECH-SCREEN")},
 [pscustomobject]@{gate="buckling_stability";status="STALE";basis="Historical P007 buckling PASS requires refresh after C2R1 freeze.";evidence=@("P007-buckling-history")},
 [pscustomobject]@{gate="torsion_rotational";status="HOLD";basis="Clocking geometry works; service torque/loosening strategy is not released.";evidence=@("R1-VERIFY","DOS-J2-C2R1")},
 [pscustomobject]@{gate="fatigue_cyclic";status="HOLD";basis="Repeated service/preload cycle evidence is open.";evidence=@("DOS-J2-C2R1")},
 [pscustomobject]@{gate="thermal";status="HOLD";basis="316L/316L reduces mismatch, but seal and fastener preload temperature response remain open.";evidence=@("DOS-J2-C2R1")},
 [pscustomobject]@{gate="dynamics_vibration";status="HOLD";basis="No explicit loosening/vibration disposition yet.";evidence=@("DOS-J2-C2R1")},
 [pscustomobject]@{gate="pressure_vacuum_sealing";status="HOLD";basis="16×1.5 gland geometry is controlled; compound, compression force and leak acceptance are open.";evidence=@("Parker","Trelleborg")},
 [pscustomobject]@{gate="fluid_cfd";status="PASS";basis="C2R1 changes external J2 package and does not change the controlled sample-flow/rod-force geometry.";evidence=@("CFD-envelope")},
 [pscustomobject]@{gate="magnetic_electromagnetic";status="HOLD";basis="Final FEMM remains after mechanical/P015/B001 freeze.";evidence=@("FEMM-plan")},
 [pscustomobject]@{gate="materials_environment";status="HOLD";basis="P003/P007 316L controlled; exact screw finish and O-ring compound remain open.";evidence=@("BOM-REC","DOS-J2-C2R1")},
 [pscustomobject]@{gate="tolerance_dimensional_chains";status="HOLD";basis="Nominal geometry passes; pilot/head worst-case clearance and production tolerances are not frozen.";evidence=@("EDR-019")},
 [pscustomobject]@{gate="manufacturability_process_capability";status="HOLD";basis="Round OD33 route is simple; M2.5 tapping in 316L, thin-wall inspection and capability acceptance remain open.";evidence=@("DOS-J2-C2R1")},
 [pscustomobject]@{gate="assembly";status=$(if($r1Cad -eq "PASS"){"PASS"}else{"HOLD"});basis="R1 assembly and interference gates pass. Service-cycle/tool-access is tracked separately under serviceability.";evidence=@("R1-VERIFY","R1-INT")},
 [pscustomobject]@{gate="serviceability";status="HOLD";basis="Removable architecture is preserved; tool feature/access and galling/service-cycle evidence remain open.";evidence=@("EDR-019","DOS-J2-C2R1")},
 [pscustomobject]@{gate="inspection_testability";status="HOLD";basis="Inspection plan and leak acceptance are not released.";evidence=@("DOS-J2-C2R1")},
 [pscustomobject]@{gate="reliability_fmea";status="HOLD";basis="Loosening/thread/seal/service failure modes still need formal disposition.";evidence=@("HEC-001")},
 [pscustomobject]@{gate="safety_regulatory_containment";status="HOLD";basis="Containment concept retained; sealing/material compatibility evidence still blocks release.";evidence=@("MARV-protection-concept")},
 [pscustomobject]@{gate="supply_chain";status="HOLD";basis="Exact M2.5 screw product/finish and O-ring compound/supplier are open.";evidence=@("BOM-REC")},
 [pscustomobject]@{gate="change_impact";status="PASS";basis="C2 rejection and C2R1 are separate controlled states; downstream nodes are reopened explicitly.";evidence=@("EDR-005","EDR-019")},
 [pscustomobject]@{gate="documentation_traceability";status=$(if($drawStatus -match "^PASS"){"PASS"}else{"HOLD"});basis="Decision/evidence traceability exists, but manufacturing drawing quality is still a release blocker.";evidence=@("DOS-J2-C2R1","DRAWING-QA")}
)

$rvm=@(
 [pscustomobject]@{id="J2-R-001";requirement="Serviceable without destructive joining";status="PASS";evidence=@("EDR-001","CI-J2")},
 [pscustomobject]@{id="J2-R-002";requirement="P003/P007 material 316L/1.4404";status="PASS";evidence=@("R1-BUILD")},
 [pscustomobject]@{id="J2-R-003";requirement="P007 OAL 35.0 mm";status=$(if(IsPass $build){"PASS"}else{"OPEN"});evidence=@("R1-BUILD")},
 [pscustomobject]@{id="J2-R-004";requirement="Radial location Ø14.10 H7/g6";status=$(if(IsPass $verify){"PASS"}else{"OPEN"});evidence=@("R1-BUILD","R1-VERIFY")},
 [pscustomobject]@{id="J2-R-005";requirement="Axial location metal-face to metal-face";status=$(if(IsPass $verify){"PASS"}else{"OPEN"});evidence=@("R1-VERIFY")},
 [pscustomobject]@{id="J2-R-006";requirement="Clocking by one M2.5-hole axis";status=$(if(IsPass $verify){"PASS"}else{"OPEN"});evidence=@("R1-VERIFY")},
 [pscustomobject]@{id="J2-R-007";requirement="Compact flange OD33.0";status=$(if(IsPass $build){"PASS"}else{"OPEN"});evidence=@("R1-BUILD")},
 [pscustomobject]@{id="J2-R-008";requirement="3×M2.5 pattern PCD26.5";status=$(if(IsPass $build){"PASS"}else{"OPEN"});evidence=@("R1-BUILD")},
 [pscustomobject]@{id="J2-R-009";requirement="No new hard interference";status=$(if(IsPass $int -and $int.new_or_unclassified_count -eq 0){"PASS"}else{"OPEN"});evidence=@("R1-INT")},
 [pscustomobject]@{id="J2-R-010";requirement="Thread/flange withstand released preload/service loads";status="OPEN";evidence=@("MECH-SCREEN")},
 [pscustomobject]@{id="J2-R-011";requirement="Static seal maintains containment";status="OPEN";evidence=@("Seal/preload")},
 [pscustomobject]@{id="J2-R-012";requirement="Serviceability after repeated cycles";status="OPEN";evidence=@("Service/galling")},
 [pscustomobject]@{id="J2-R-013";requirement="Production tolerances preserve seal/clearances";status="OPEN";evidence=@("EDR-019")},
 [pscustomobject]@{id="J2-R-014";requirement="P007 structural margins acceptable after J2 freeze";status="STALE";evidence=@("Static/buckling history")},
 [pscustomobject]@{id="J2-R-015";requirement="BOM/drawings/technology match release";status=$(if($bomStatus -eq "PASS" -and $drawStatus -match "^PASS"){"PASS"}else{"HOLD"});evidence=@("BOM-REC","DRAWING-QA")}
)

$evidence=@(
 Info "reports\cad\current\K01_GATE04D_C2R1_TYPED_BUILD.json" "R1-BUILD"
 Info "reports\cad\current\K01_GATE04D_C2R1_VERIFY.json" "R1-VERIFY"
 Info "reports\cad\current\K01_GATE04D_C2R1_INTERFERENCE.json" "R1-INT"
 Info "reports\bom\K01_BOM_RECONCILIATION_study_c2r1.json" "BOM-REC"
 Info "reports\cad\current\K01_GATE04D_C2R1_TYPED_DRAWINGS_V2.json" "DRAWING-V2"
 Info "reports\cad\current\K01_DRAWING_QUALITY_P003_C2R1_v1.json" "DRAWING-QA"
 Info "reports\analysis\current\K01_J2_C2_MECHANICAL_SCREEN_v1.json" "MECH-SCREEN"
 Info "reports\analysis\current\K01_C2_PILOT_INTERFERENCE_ROOT_CAUSE_v1.json" "ROOTCAUSE"
)

$next=$tasks|Where-Object{$_.status -notmatch "^(PASS|PASS_|SCREEN_PASS)"}|Select-Object -First 1
$state=[pscustomobject]@{
 schema="k01_derived_state_v7"
 generated=(Get-Date).ToString("o")
 active_design="Gate04D-C2R1"
 tasks=$tasks
 next_task=$next
 eds=$eds
 rvm=$rvm
 evidence=$evidence
 metrics=[pscustomobject]@{
   task_pass=@($tasks|Where-Object{$_.status -match "^(PASS|PASS_|SCREEN_PASS)"}).Count
   task_total=$tasks.Count
   eds_pass=@($eds|Where-Object{$_.status -eq "PASS"}).Count
   eds_total=$eds.Count
   bom_release_blockers=if($bomRec){$bomRec.release_blockers}else{$null}
   bom_metadata_projection=if($bomRec){$bomRec.metadata_projection_required}else{$null}
 }
}

# Derive a stable hash excluding timestamp and persist only true transitions.
$hashObject=[pscustomobject]@{active_design=$state.active_design;tasks=$tasks;eds=$eds;rvm=$rvm;evidence=$evidence}
$raw=$hashObject|ConvertTo-Json -Depth 30 -Compress
$sha=[Security.Cryptography.SHA256]::Create()
$hash=[BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($raw))).Replace("-","")
$state|Add-Member -NotePropertyName state_hash -NotePropertyValue $hash

$out=P "control\state\K01_STATE_CURRENT.json"
$events=P "control\state\K01_EVENT_LEDGER.jsonl"
$previous=$null
if(Test-Path -LiteralPath $out){try{$previous=Get-Content -LiteralPath $out -Raw -Encoding UTF8|ConvertFrom-Json}catch{}}

if($null -eq $previous -or $previous.state_hash -ne $hash){
    $now=(Get-Date).ToString("o")
    if($previous){
        $old=@{};foreach($t in $previous.tasks){$old[$t.id]=$t.status}
        foreach($t in $tasks){
            $before=if($old.ContainsKey($t.id)){$old[$t.id]}else{"<NEW>"}
            if($before -ne $t.status){
                [pscustomobject]@{schema="k01_event_v1";time=$now;type="TASK_STATUS_CHANGED";task_id=$t.id;from=$before;to=$t.status;active_design=$state.active_design;state_hash=$hash}|ConvertTo-Json -Compress|Add-Content -LiteralPath $events -Encoding UTF8
            }
        }
    }else{
        [pscustomobject]@{schema="k01_event_v1";time=$now;type="STATE_INITIALIZED";active_design=$state.active_design;state_hash=$hash}|ConvertTo-Json -Compress|Add-Content -LiteralPath $events -Encoding UTF8
    }
    [pscustomobject]@{schema="k01_event_v1";time=$now;type="EVIDENCE_STATE_REDUCED";active_design=$state.active_design;state_hash=$hash;evidence_roles=@($evidence|Where-Object{$_.exists}|ForEach-Object{$_.role})}|ConvertTo-Json -Compress|Add-Content -LiteralPath $events -Encoding UTF8
}

$state|ConvertTo-Json -Depth 30|Set-Content -LiteralPath $out -Encoding UTF8
$tasks|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (P "control\state\K01_TASK_REGISTER_CURRENT.json") -Encoding UTF8
$eds|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (P "control\state\K01_EDS_DERIVED_CURRENT.json") -Encoding UTF8
$rvm|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (P "control\state\K01_RVM_DERIVED_CURRENT.json") -Encoding UTF8
$evidence|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (P "control\state\K01_EVIDENCE_INDEX_CURRENT.json") -Encoding UTF8

$state|ConvertTo-Json -Depth 30
