$ErrorActionPreference = "Stop"
$Here=$PSScriptRoot
$Repo=(Resolve-Path (Join-Path $Here "..\..")).Path
$Data=Join-Path $Here "data"
$Registry=Get-Content (Join-Path $Data "K01_FILE_REGISTRY_v3.json") -Raw -Encoding UTF8|ConvertFrom-Json
$Profiles=Get-Content (Join-Path $Data "K01_MACHINE_PROFILES_v2.json") -Raw -Encoding UTF8|ConvertFrom-Json
$Profile=$Profiles.profiles.($Profiles.active_profile)
$Cad=$Profile.cad_root
$Port=8765

function Root-For($n){if($n -eq "cad"){return $Cad};return $Repo}
function Resolve-Entry($e){
 $root=Root-For $e.root
 foreach($rel in @($e.candidates)){if(-not $rel){continue};$p=[IO.Path]::GetFullPath((Join-Path $root $rel));if(Test-Path $p){return $p}}
 $matches=@()
 foreach($pat in @($e.patterns)){if(-not $pat){continue};$matches+=@(Get-ChildItem -Path (Join-Path $root $pat) -File -ErrorAction SilentlyContinue)}
 if($matches.Count -gt 0){return ($matches|Sort-Object LastWriteTime -Descending|Select-Object -First 1).FullName}
 if(@($e.candidates).Count -gt 0){return [IO.Path]::GetFullPath((Join-Path $root @($e.candidates)[0]))}
 return ""
}
function JsonBytes($o){[Text.Encoding]::UTF8.GetBytes(($o|ConvertTo-Json -Depth 20))}
function Send($s,$code,$type,[byte[]]$body){$st=if($code -eq 200){"OK"}elseif($code -eq 404){"Not Found"}else{"Error"};$h="HTTP/1.1 $code $st`r`nContent-Type: $type`r`nContent-Length: $($body.Length)`r`nConnection: close`r`n`r`n";$hb=[Text.Encoding]::ASCII.GetBytes($h);$s.Write($hb,0,$hb.Length);$s.Write($body,0,$body.Length);$s.Flush()}
function Git-Out{param([string[]]$GitArgs);try{if(-not(Get-Command git -ErrorAction SilentlyContinue)){return "GIT_NOT_FOUND"};return (& git -C $Repo @GitArgs 2>&1|Out-String).Trim()}catch{return "ERROR: $($_.Exception.Message)"}}
function Git-State{$status=Git-Out @("status","--porcelain=v1");$lines=@();if($status -and -not $status.StartsWith("ERROR:") -and $status -ne "GIT_NOT_FOUND"){$lines=$status -split "`r?`n"};[pscustomobject]@{branch=Git-Out @("branch","--show-current");last_commit=Git-Out @("log","-1","--format=%H|%cI|%s");origin=Git-Out @("remote","get-url","origin");dirty_count=@($lines).Count;untracked_count=@($lines|Where-Object{$_.StartsWith("??")}).Count;status_lines=$lines}}
function Read-JsonSafe($p){if(-not(Test-Path $p)){return $null};try{return Get-Content $p -Raw -Encoding UTF8|ConvertFrom-Json}catch{return [pscustomobject]@{status="PARSE_ERROR";error=$_.Exception.Message}}}
function Latest-Log($pattern){Get-ChildItem (Join-Path $Repo "reports\cad\current") -Filter $pattern -File -ErrorAction SilentlyContinue|Sort-Object LastWriteTime -Descending|Select-Object -First 1}
function Report-State{
 $build=Join-Path $Repo "reports\cad\current\K01_GATE04D_C2_TYPED_BUILD.json";$verify=Join-Path $Repo "reports\cad\current\K01_GATE04D_C2_VERIFY.json";$int=Join-Path $Repo "reports\cad\current\K01_GATE04D_C2_INTERFERENCE.json";$bom=Join-Path $Repo "reports\bom\K01_BOM_AUDIT_study_c2.json"
 [pscustomobject]@{build=Read-JsonSafe $build;verify=Read-JsonSafe $verify;interference=Read-JsonSafe $int;bom=Read-JsonSafe $bom;build_log=(Latest-Log "K01_GATE04D_C2_TYPED_BUILD_*.log").FullName;verify_log=(Latest-Log "K01_GATE04D_C2_VERIFY_*.log").FullName;interference_log=(Latest-Log "K01_GATE04D_C2_INTERFERENCE_*.log").FullName}
}
function Artifact-State{$rows=@();foreach($e in $Registry.entries){$p=Resolve-Entry $e;$rows+=[pscustomobject]@{id=$e.id;name=$e.name;domain=$e.domain;resolved=$p;exists=(Test-Path $p);modified=if(Test-Path $p){(Get-Item $p).LastWriteTime.ToString("s")}else{""}}};[pscustomobject]@{repo_root=$Repo;cad_root=$Cad;entries=$rows}}
function Add-HandoffFile($src,$dstRoot,$cat,[ref]$manifest){if(-not $src -or -not(Test-Path $src -PathType Leaf)){return};$d=Join-Path $dstRoot $cat;New-Item $d -ItemType Directory -Force|Out-Null;$dst=Join-Path $d ([IO.Path]::GetFileName($src));Copy-Item $src $dst -Force;$manifest.Value+=[pscustomobject]@{category=$cat;name=[IO.Path]::GetFileName($src);source=$src;sha256=(Get-FileHash $src -Algorithm SHA256).Hash;modified=(Get-Item $src).LastWriteTime.ToString("s")}}
function Build-Handoff{
 $out=Join-Path $Repo "handoff\current";New-Item $out -ItemType Directory -Force|Out-Null;$tmp=Join-Path $out "K01_AI_HANDOFF_CURRENT";if(Test-Path $tmp){Remove-Item $tmp -Recurse -Force};New-Item $tmp -ItemType Directory|Out-Null;$m=@()
 foreach($id in @("MASTER","EDS001","EDR005","CI-J2","SOURCE-REG","C2-BUILD","C2-VERIFY","C2-INT","BOM-C2","BOM-AUDIT-C2","DRAW-P003-PDF","DRAW-P007-PDF","AI-CURRENT")){$e=$Registry.entries|Where-Object{$_.id -eq $id}|Select-Object -First 1;if($e){Add-HandoffFile (Resolve-Entry $e) $tmp $e.domain ([ref]$m)}}
 foreach($pat in @("K01_GATE04D_C2_TYPED_BUILD_*.log","K01_GATE04D_C2_VERIFY_*.log","K01_GATE04D_C2_INTERFERENCE_*.log")){$p=Latest-Log $pat;if($p){Add-HandoffFile $p.FullName $tmp "EVIDENCE" ([ref]$m)}}
 foreach($rel in @("control\decision_system\K01_J2_C2_REQUIREMENTS_VERIFICATION_MATRIX_v1.csv","control\system\K01_DEPENDENCY_GRAPH_v2.json","docs\design\trade_studies\K01_J2_COMPACT_TRADE_STUDY_v2.md","cad_api\gates\gate04d_c2\K01_GATE04D_C2_PARAMS_v1.json","cad_api\gates\gate04d_c2\K01_GATE04D_C2_DESIGN_INPUT_v1.json")){Add-HandoffFile (Join-Path $Repo $rel) $tmp "CONTROL" ([ref]$m)}
 [pscustomobject]@{schema="k01_ai_handoff_manifest_v1";created=(Get-Date).ToString("o");repo=$Repo;cad=$Cad;files=$m}|ConvertTo-Json -Depth 20|Set-Content (Join-Path $tmp "MANIFEST.json") -Encoding UTF8
 $zip=Join-Path $out "K01_AI_HANDOFF_CURRENT.zip";if(Test-Path $zip){Remove-Item $zip -Force};Compress-Archive -Path (Join-Path $tmp "*") -DestinationPath $zip -Force;return $zip
}
$Actions=@{
 "RUN_C2_BUILD_VERIFY"=Join-Path $Repo "cad_api\gates\gate04d_c2\00_GATE04D_C2_BUILD_AND_VERIFY.cmd"
 "RUN_C2_INTERFERENCE"=Join-Path $Repo "cad_api\gates\gate04d_c2\03_GATE04D_C2_INTERFERENCE_QA.cmd"
 "RUN_BOM_C2"=Join-Path $Repo "cad_api\bom\RUN_K01_BOM.cmd"
 "RUN_C2_DRAFT_DRAWINGS"=Join-Path $Repo "cad_api\gates\gate04d_c2\04_GATE04D_C2_DRAFT_DRAWINGS.cmd"
}
function Query-Id($t){if($t -match '[?&]id=([^&]+)'){return [uri]::UnescapeDataString($matches[1])};return ""}
$listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$Port);$listener.Start()
Write-Host "================================================================================";Write-Host "MARVILON K01 MEDTAS - Engineering Control Center v4";Write-Host "================================================================================";Write-Host "Repo: $Repo";Write-Host "CAD : $Cad";Write-Host "URL : http://127.0.0.1:$Port/";Start-Process "http://127.0.0.1:$Port/"
while($true){$client=$listener.AcceptTcpClient();try{$stream=$client.GetStream();$reader=New-Object IO.StreamReader($stream,[Text.Encoding]::ASCII,$false,8192,$true);$rl=$reader.ReadLine();while(($line=$reader.ReadLine()) -ne $null -and $line -ne ""){};if(-not $rl){continue};$target=$rl.Split(" ")[1]
 if($target -eq "/" -or $target.StartsWith("/index")){Send $stream 200 "text/html; charset=utf-8" ([IO.File]::ReadAllBytes((Join-Path $Here "K01_Command_Center_v4.html")))}
 elseif($target.StartsWith("/api/files")){Send $stream 200 "application/json; charset=utf-8" (JsonBytes (Artifact-State))}
 elseif($target.StartsWith("/api/reports")){Send $stream 200 "application/json; charset=utf-8" (JsonBytes (Report-State))}
 elseif($target.StartsWith("/api/git")){Send $stream 200 "application/json; charset=utf-8" (JsonBytes (Git-State))}
 elseif($target.StartsWith("/api/handoff/build")){$p=Build-Handoff;Start-Process explorer.exe -ArgumentList "/select,`"$p`"";Send $stream 200 "application/json; charset=utf-8" (JsonBytes @{ok=$true;path=$p})}
 elseif($target.StartsWith("/api/action")){$id=Query-Id $target;if(-not $Actions.ContainsKey($id)){Send $stream 404 "application/json" (JsonBytes @{error="unknown action"});continue};$p=$Actions[$id];if(-not(Test-Path $p)){Send $stream 404 "application/json" (JsonBytes @{error="action missing";path=$p});continue};Start-Process -FilePath "cmd.exe" -ArgumentList "/k","`"$p`"" -WorkingDirectory ([IO.Path]::GetDirectoryName($p));Send $stream 200 "application/json" (JsonBytes @{ok=$true;action=$id;path=$p})}
 elseif($target.StartsWith("/api/open") -or $target.StartsWith("/api/reveal")){$id=Query-Id $target;$e=$Registry.entries|Where-Object{$_.id -eq $id}|Select-Object -First 1;if(-not $e){Send $stream 404 "application/json" (JsonBytes @{error="unknown id"});continue};$p=Resolve-Entry $e;if(-not(Test-Path $p)){Send $stream 404 "application/json" (JsonBytes @{error="missing";path=$p});continue};if($target.StartsWith("/api/reveal")){Start-Process explorer.exe -ArgumentList "/select,`"$p`""}else{Start-Process -FilePath $p};Send $stream 200 "application/json" (JsonBytes @{ok=$true;path=$p})}
 else{Send $stream 404 "text/plain; charset=utf-8" ([Text.Encoding]::UTF8.GetBytes("Not found"))}
 }catch{try{Send $stream 500 "text/plain; charset=utf-8" ([Text.Encoding]::UTF8.GetBytes($_.Exception.Message))}catch{}}finally{$client.Close()}}
