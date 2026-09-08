param([string]$Mode="c2")
$ErrorActionPreference="Stop"
$Repo=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$suffix=if($Mode -eq "r1"){"study_c2r1"}else{"study_c2"}
$Audit=Join-Path $Repo ("reports\bom\K01_BOM_AUDIT_"+$suffix+".json")
$MapPath=Join-Path $Repo "control\system\K01_PART_IDENTITY_AUTHORITY_v1.json"
$OutJson=Join-Path $Repo ("bom\K01_BOM_RECONCILED_"+$suffix+".json")
$OutCsv=Join-Path $Repo ("bom\K01_BOM_RECONCILED_"+$suffix+".csv")
$Rpt=Join-Path $Repo ("reports\bom\K01_BOM_RECONCILIATION_"+$suffix+".json")
if(-not(Test-Path $Audit)){throw "Raw CAD BOM audit missing: $Audit"}
if(-not(Test-Path $MapPath)){throw "Identity authority missing: $MapPath"}
$a=Get-Content $Audit -Raw -Encoding UTF8|ConvertFrom-Json
$m=Get-Content $MapPath -Raw -Encoding UTF8|ConvertFrom-Json
$rows=@();$releaseBlockers=0;$metadataSync=0;$unmapped=0
foreach($r in $a.rows){
 $text=($r.path+"|"+$r.observed_part_no)
 $auth=$null
 foreach($p in $m.parts){foreach($token in @($p.match)){if($text -like "*$token*"){$auth=$p;break}};if($auth){break}}
 if(-not $auth){
   $unmapped++;$releaseBlockers++
   $rows += [pscustomobject]@{part_no=$r.observed_part_no;description=$r.description;qty=$r.qty;unit=$r.qty_unit;make_buy="";material_authority="UNMAPPED";material_status="HOLD";cad_native_material=$r.solidworks_material;cad_partno=$r.observed_part_no;cad_identity_source=$r.identity_source;metadata_sync="UNMAPPED";release="HOLD";path=$r.path}
   continue
 }
 $meta="SYNCED"
 if($r.identity_source -ne "CUSTOM_PROPERTY" -or $r.observed_part_no -ne $auth.part_no -or [string]::IsNullOrWhiteSpace($r.description)){$meta="PROJECTION_REQUIRED";$metadataSync++}
 $matStat=$auth.material_status
 $release="PASS"
 if($matStat -match "OPEN|REVIEW|CONDITIONAL"){$release="HOLD";$releaseBlockers++}
 $rows += [pscustomobject]@{part_no=$auth.part_no;description=$auth.description;qty=$r.qty;unit=($(if($r.qty_unit){$r.qty_unit}else{"ea"}));make_buy=$auth.make_buy;material_authority=$auth.material_authority;material_status=$matStat;cad_native_material=$r.solidworks_material;cad_partno=$r.observed_part_no;cad_identity_source=$r.identity_source;metadata_sync=$meta;release=$release;path=$r.path}
}
$status=if($releaseBlockers -eq 0 -and $unmapped -eq 0){"PASS"}else{"HOLD"}
$out=[pscustomobject]@{schema="k01_bom_reconciled_v1";created=(Get-Date).ToString("o");status=$status;source_audit=$Audit;row_count=$rows.Count;release_blockers=$releaseBlockers;metadata_projection_required=$metadataSync;unmapped=$unmapped;rows=$rows}
$out|ConvertTo-Json -Depth 12|Set-Content $OutJson -Encoding UTF8
$out|ConvertTo-Json -Depth 12|Set-Content $Rpt -Encoding UTF8
$rows|Export-Csv $OutCsv -NoTypeInformation -Encoding UTF8
Write-Host "RECONCILED BOM $status rows=$($rows.Count) release_blockers=$releaseBlockers metadata_projection_required=$metadataSync unmapped=$unmapped"
Write-Host "JSON: $OutJson"
Write-Host "CSV : $OutCsv"
exit $(if($status -eq "PASS"){0}else{2})
