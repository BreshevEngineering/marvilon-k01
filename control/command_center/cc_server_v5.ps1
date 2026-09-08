$ErrorActionPreference="Stop"
$Here=$PSScriptRoot
$Repo=(Resolve-Path (Join-Path $Here "..\..")).Path
$Data=Join-Path $Here "data"
$Registry=Get-Content (Join-Path $Data "K01_FILE_REGISTRY_v5.json") -Raw -Encoding UTF8|ConvertFrom-Json
$Profiles=Get-Content (Join-Path $Data "K01_MACHINE_PROFILES_v2.json") -Raw -Encoding UTF8|ConvertFrom-Json
$Profile=$Profiles.profiles.($Profiles.active_profile)
$Cad=$Profile.cad_root
$Port=8765

function Root-For($n){if($n -eq "cad"){return $Cad};return $Repo}
function Values($e,$name){if($e.PSObject.Properties.Name -contains $name){return @($e.$name|Where-Object{$_})};return @()}
function Resolve-Entry($e){
 $root=Root-For $e.root
 foreach($rel in (Values $e "candidates")){$p=[IO.Path]::GetFullPath((Join-Path $root $rel));if(Test-Path $p -PathType Leaf){return $p}}
 $matches=@()
 foreach($pat in (Values $e "patterns")){$matches+=@(Get-ChildItem -Path (Join-Path $root $pat) -File -ErrorAction SilentlyContinue)}
 if($matches.Count -gt 0){return ($matches|Sort-Object LastWriteTime -Descending|Select-Object -First 1).FullName}
 $cand=Values $e "candidates";if($cand.Count -gt 0){return [IO.Path]::GetFullPath((Join-Path $root $cand[0]))}
 return ""
}
function JsonBytes($o){[Text.Encoding]::UTF8.GetBytes(($o|ConvertTo-Json -Depth 30))}
function Send($s,$code,$type,[byte[]]$body){$st=if($code -eq 200){"OK"}elseif($code -eq 404){"Not Found"}else{"Error"};$h="HTTP/1.1 $code $st`r`nContent-Type: $type`r`nContent-Length: $($body.Length)`r`nConnection: close`r`n`r`n";$hb=[Text.Encoding]::ASCII.GetBytes($h);$s.Write($hb,0,$hb.Length);$s.Write($body,0,$body.Length);$s.Flush()}
function ReadJson($p){if(-not(Test-Path $p -PathType Leaf)){return $null};try{return Get-Content $p -Raw -Encoding UTF8|ConvertFrom-Json}catch{return [pscustomobject]@{status="PARSE_ERROR";error=$_.Exception.Message}}}
function Info($p){if(Test-Path $p -PathType Leaf){$i=Get-Item $p;return [pscustomobject]@{path=$p;exists=$true;modified=$i.LastWriteTime.ToString("s");bytes=$i.Length}};return [pscustomobject]@{path=$p;exists=$false;modified="";bytes=0}}
function Git-Out{param([string[]]$GitArgs);try{if(-not(Get-Command git -ErrorAction SilentlyContinue)){return "GIT_NOT_FOUND"};return (& git -C $Repo @GitArgs 2>&1|Out-String).Trim()}catch{return "ERROR: $($_.Exception.Message)"}}
function Git-State{$st=Git-Out @("status","--porcelain=v1");$ln=@();if($st -and -not $st.StartsWith("ERROR:") -and $st -ne "GIT_NOT_FOUND"){$ln=$st -split "`r?`n"};[pscustomobject]@{branch=Git-Out @("branch","--show-current");last_commit=Git-Out @("log","-1","--format=%H|%cI|%s");origin=Git-Out @("remote","get-url","origin");dirty_count=@($ln).Count;untracked_count=@($ln|Where-Object{$_.StartsWith("??")}).Count;status_lines=$ln}}
function Artifact-State{$r=@();foreach($e in $Registry.entries){$p=Resolve-Entry $e;$x=Info $p;$r+=[pscustomobject]@{id=$e.id;name=$e.name;domain=$e.domain;resolved=$p;exists=$x.exists;modified=$x.modified;bytes=$x.bytes}};[pscustomobject]@{repo_root=$Repo;cad_root=$Cad;entries=$r}}
function P($rel){Join-Path $Repo $rel}
function Current-State{
 $build=ReadJson (P "reports\cad\current\K01_GATE04D_C2_TYPED_BUILD.json")
 $verify=ReadJson (P "reports\cad\current\K01_GATE04D_C2_VERIFY.json")
 $rawInt=ReadJson (P "reports\cad\current\K01_GATE04D_C2_INTERFERENCE.json")
 $delta=ReadJson (P "reports\cad\current\K01_GATE04D_C2_INTERFERENCE_DELTA.json")
 $rawBom=ReadJson (P "reports\bom\K01_BOM_AUDIT_study_c2.json")
 $recBom=ReadJson (P "bom\K01_BOM_RECONCILED_study_c2.json")
 $draw=ReadJson (P "reports\cad\current\K01_GATE04D_C2_TYPED_DRAWINGS.json")
 $mech=ReadJson (P "reports\analysis\current\K01_J2_C2_MECHANICAL_SCREEN_v1.json")
 $tasks=@()
 $tasks += [pscustomobject]@{id="T01";name="C2 native build";status=if($build){$build.status}else{"OPEN"};action="RUN_C2_BUILD_VERIFY";kind="AUTOMATED";why="Native candidate geometry"}
 $tasks += [pscustomobject]@{id="T02";name="C2 assembly verify";status=if($verify){$verify.status}else{"OPEN"};action="RUN_C2_BUILD_VERIFY";kind="AUTOMATED";why="Pilot / metal face / clocking mates"}
 $tasks += [pscustomobject]@{id="T03";name="Stable-vs-C2 interference delta";status=if($delta){$delta.status}else{"OPEN"};action="RUN_C2_DELTA";kind="AUTOMATED";why="Resolve raw P003/P006 interference by comparison, not whitelist"}
 $tasks += [pscustomobject]@{id="T04";name="M2.5/thread preliminary mechanical screen";status=if($mech){$mech.status}else{"OPEN"};action="OPEN_C2_MECH";kind="ENGINEERING";why="Pressure/thread/head-bearing screen"}
 $tasks += [pscustomobject]@{id="T05";name="O-ring compound + required preload";status="OPEN";action="OPEN_EDR005";kind="ENGINEERING_INPUT";why="Seal material/force controls minimum clamp load"}
 $tasks += [pscustomobject]@{id="T06";name="Local flange/contact structural verification";status="OPEN";action="";kind="ANALYSIS";why="Needs final preload from T05"}
 $tasks += [pscustomobject]@{id="T07";name="Thermal + service/galling closure";status="OPEN";action="OPEN_EDR005";kind="ENGINEERING";why="Preload drift and repeated maintenance"}
 $tasks += [pscustomobject]@{id="T08";name="P007 static + buckling refresh";status="STALE";action="";kind="SOLVER";why="Refresh after C2 flange/preload freeze"}
 $tasks += [pscustomobject]@{id="T09";name="C2 reconciled BOM";status=if($recBom){$recBom.status}else{"OPEN"};action="RUN_BOM_PIPELINE";kind="AUTOMATED";why="CAD quantities + controlled identity/material state"}
 $tasks += [pscustomobject]@{id="T10";name="C2 draft drawings";status=if($draw){$draw.status}else{"OPEN"};action="RUN_C2_DRAWINGS";kind="AUTOMATED";why="DRAFT evidence only until release gates pass"}
 $tasks += [pscustomobject]@{id="T11";name="FEMM impact review / final FEMM";status="OPEN";action="";kind="SOLVER";why="After mechanical/P015/magnet data freeze"}
 $tasks += [pscustomobject]@{id="T12";name="Atomic promotion / release";status="HOLD";action="";kind="RELEASE";why="All mandatory EDS gates must PASS"}
 $next=$tasks|Where-Object{$_.status -notmatch "^(PASS|SCREEN_PASS)"}|Select-Object -First 1
 [pscustomobject]@{build=$build;verify=$verify;raw_interference=$rawInt;delta_interference=$delta;raw_bom=$rawBom;reconciled_bom=$recBom;drawings=$draw;mechanical=$mech;tasks=$tasks;next_task=$next}
}
function QueryId($t){if($t -match '[?&]id=([^&]+)'){return [uri]::UnescapeDataString($matches[1])};return ""}
$Actions=@{
 "RUN_C2_BUILD_VERIFY"=P "cad_api\gates\gate04d_c2\00_GATE04D_C2_BUILD_AND_VERIFY.cmd"
 "RUN_C2_DELTA"=P "cad_api\gates\gate04d_c2\03B_GATE04D_C2_INTERFERENCE_DELTA_QA.cmd"
 "RUN_BOM_PIPELINE"=P "cad_api\bom\RUN_K01_BOM_PIPELINE_C2.cmd"
 "RUN_C2_DRAWINGS"=P "cad_api\gates\gate04d_c2\04_GATE04D_C2_DRAFT_DRAWINGS.cmd"
}
function AddFile($src,$dst,$cat,[ref]$m){if(-not $src -or -not(Test-Path $src -PathType Leaf)){return};$d=Join-Path $dst $cat;New-Item $d -ItemType Directory -Force|Out-Null;$to=Join-Path $d ([IO.Path]::GetFileName($src));Copy-Item $src $to -Force;$m.Value+=[pscustomobject]@{category=$cat;name=[IO.Path]::GetFileName($src);source=$src;sha256=(Get-FileHash $src -Algorithm SHA256).Hash;modified=(Get-Item $src).LastWriteTime.ToString("s")}}
function BuildHandoff{
 $out=P "handoff\current";New-Item $out -ItemType Directory -Force|Out-Null;$tmp=Join-Path $out "K01_AI_HANDOFF_CURRENT";if(Test-Path $tmp){Remove-Item $tmp -Recurse -Force};New-Item $tmp -ItemType Directory|Out-Null;$m=@()
 foreach($e in $Registry.entries){if($e.domain -in @("CONTROL","DECISION","CONFIGURATION","LIVE_REPORT","LIVE_LOG","ANALYSIS","BOM","DRAWING","HANDOFF")){$p=Resolve-Entry $e;if($e.id -ne "AI-HANDOFF"){AddFile $p $tmp $e.domain ([ref]$m)}}}
 foreach($rel in @("control\evidence\K01_SOURCE_REGISTRY_v1.json","control\evidence\ERR-P003-P006-THREAD-001.json","control\system\K01_PART_IDENTITY_AUTHORITY_v1.json","docs\design\trade_studies\K01_J2_COMPACT_TRADE_STUDY_v2.md","cad_api\gates\gate04d_c2\K01_GATE04D_C2_PARAMS_v1.json","cad_api\gates\gate04d_c2\K01_GATE04D_C2_DESIGN_INPUT_v1.json")){AddFile (P $rel) $tmp "CONTROL" ([ref]$m)}
 [pscustomobject]@{schema="k01_ai_handoff_manifest_v2";created=(Get-Date).ToString("o");repo=$Repo;cad=$Cad;files=$m}|ConvertTo-Json -Depth 20|Set-Content (Join-Path $tmp "MANIFEST.json") -Encoding UTF8
 $zip=Join-Path $out "K01_AI_HANDOFF_CURRENT.zip";if(Test-Path $zip){Remove-Item $zip -Force};Compress-Archive -Path (Join-Path $tmp "*") -DestinationPath $zip -Force;return $zip
}

$listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$Port);$listener.Start()
Write-Host "================================================================================";Write-Host "MARVILON K01 MEDTAS - Engineering Control Center v5";Write-Host "================================================================================";Write-Host "Repo: $Repo";Write-Host "CAD : $Cad";Write-Host "URL : http://127.0.0.1:$Port/";Start-Process "http://127.0.0.1:$Port/"
while($true){$client=$listener.AcceptTcpClient();try{$stream=$client.GetStream();$reader=New-Object IO.StreamReader($stream,[Text.Encoding]::ASCII,$false,8192,$true);$rl=$reader.ReadLine();while(($line=$reader.ReadLine()) -ne $null -and $line -ne ""){};if(-not $rl){continue};$target=$rl.Split(" ")[1]
 if($target -eq "/" -or $target.StartsWith("/index")){Send $stream 200 "text/html; charset=utf-8" ([IO.File]::ReadAllBytes((Join-Path $Here "K01_Command_Center_v5.html")))}
 elseif($target.StartsWith("/api/state")){Send $stream 200 "application/json; charset=utf-8" (JsonBytes (Current-State))}
 elseif($target.StartsWith("/api/files")){Send $stream 200 "application/json; charset=utf-8" (JsonBytes (Artifact-State))}
 elseif($target.StartsWith("/api/git")){Send $stream 200 "application/json; charset=utf-8" (JsonBytes (Git-State))}
 elseif($target.StartsWith("/api/handoff/build")){$p=BuildHandoff;Start-Process explorer.exe -ArgumentList "/select,`"$p`"";Send $stream 200 "application/json; charset=utf-8" (JsonBytes @{ok=$true;path=$p})}
 elseif($target.StartsWith("/api/action")){$id=QueryId $target;if($id -eq "OPEN_C2_MECH"){$p=P "reports\analysis\current\K01_J2_C2_MECHANICAL_SCREEN_v1.json";Start-Process $p;Send $stream 200 "application/json" (JsonBytes @{ok=$true;path=$p});continue};if($id -eq "OPEN_EDR005"){$p=P "control\decision_system\records\EDR-005_J2_COMPACT_FLANGE_v3.json";Start-Process $p;Send $stream 200 "application/json" (JsonBytes @{ok=$true;path=$p});continue};if(-not $Actions.ContainsKey($id)){Send $stream 404 "application/json" (JsonBytes @{error="unknown action"});continue};$p=$Actions[$id];if(-not(Test-Path $p)){Send $stream 404 "application/json" (JsonBytes @{error="action missing";path=$p});continue};Start-Process -FilePath "cmd.exe" -ArgumentList "/k","`"$p`"" -WorkingDirectory ([IO.Path]::GetDirectoryName($p));Send $stream 200 "application/json" (JsonBytes @{ok=$true;action=$id;path=$p})}
 elseif($target.StartsWith("/api/open") -or $target.StartsWith("/api/reveal")){$id=QueryId $target;$e=$Registry.entries|Where-Object{$_.id -eq $id}|Select-Object -First 1;if(-not $e){Send $stream 404 "application/json" (JsonBytes @{error="unknown id"});continue};$p=Resolve-Entry $e;if(-not(Test-Path $p -PathType Leaf)){Send $stream 404 "application/json" (JsonBytes @{error="missing";path=$p});continue};if($target.StartsWith("/api/reveal")){Start-Process explorer.exe -ArgumentList "/select,`"$p`""}else{Start-Process -FilePath $p};Send $stream 200 "application/json" (JsonBytes @{ok=$true;path=$p})}
 else{Send $stream 404 "text/plain; charset=utf-8" ([Text.Encoding]::UTF8.GetBytes("Not found"))}
 }catch{try{Send $stream 500 "text/plain; charset=utf-8" ([Text.Encoding]::UTF8.GetBytes($_.Exception.Message))}catch{}}finally{$client.Close()}}
