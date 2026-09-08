$ErrorActionPreference="Stop"
$Here=$PSScriptRoot
$Repo=(Resolve-Path (Join-Path $Here "..\..")).Path
$Data=Join-Path $Here "data"
$Registry=Get-Content (Join-Path $Data "K01_FILE_REGISTRY_v7.json") -Raw -Encoding UTF8|ConvertFrom-Json
$Profiles=Get-Content (Join-Path $Data "K01_MACHINE_PROFILES_v2.json") -Raw -Encoding UTF8|ConvertFrom-Json
$Profile=$Profiles.profiles.($Profiles.active_profile)
$Cad=$Profile.cad_root
$Port=8765

function Root-For($n){if($n -eq "cad"){return $Cad};return $Repo}
function Values($e,$name){if($e.PSObject.Properties.Name -contains $name){return @($e.$name|Where-Object{$_})};return @()}
function Resolve-Entry($e){
    $root=Root-For $e.root
    foreach($rel in (Values $e "candidates")){
        if([string]::IsNullOrWhiteSpace($rel)){continue}
        $p=[IO.Path]::GetFullPath((Join-Path $root $rel))
        if(Test-Path -LiteralPath $p -PathType Leaf){return $p}
    }
    $matches=@()
    foreach($pat in (Values $e "patterns")){
        if([string]::IsNullOrWhiteSpace($pat)){continue}
        try{$matches+=@(Get-ChildItem -Path (Join-Path $root $pat) -File -ErrorAction SilentlyContinue)}catch{}
    }
    if($matches.Count -gt 0){return ($matches|Sort-Object LastWriteTime -Descending|Select-Object -First 1).FullName}
    $cand=Values $e "candidates"
    if($cand.Count -gt 0){return [IO.Path]::GetFullPath((Join-Path $root $cand[0]))}
    return $null
}
function SafeInfo($p){
    if([string]::IsNullOrWhiteSpace($p)){return [pscustomobject]@{path="";exists=$false;modified="";bytes=0}}
    try{if(Test-Path -LiteralPath $p -PathType Leaf){$i=Get-Item -LiteralPath $p;return [pscustomobject]@{path=$p;exists=$true;modified=$i.LastWriteTime.ToString("s");bytes=$i.Length}}}catch{}
    return [pscustomobject]@{path=$p;exists=$false;modified="";bytes=0}
}
function P($rel){Join-Path $Repo $rel}
function ReadJsonPath($p){
    if([string]::IsNullOrWhiteSpace($p) -or -not(Test-Path -LiteralPath $p -PathType Leaf)){return $null}
    try{return Get-Content -LiteralPath $p -Raw -Encoding UTF8|ConvertFrom-Json}catch{return [pscustomobject]@{status="PARSE_ERROR";error=$_.Exception.Message;path=$p}}
}
function JsonBytes($o){[Text.Encoding]::UTF8.GetBytes(($o|ConvertTo-Json -Depth 50 -Compress))}
function TextBytes($s){[Text.Encoding]::UTF8.GetBytes([string]$s)}
function Send($s,$code,$type,[byte[]]$body){
    $st=if($code -eq 200){"OK"}elseif($code -eq 404){"Not Found"}else{"Error"}
    $h="HTTP/1.1 $code $st`r`nContent-Type: $type`r`nCache-Control: no-store`r`nContent-Length: $($body.Length)`r`nConnection: close`r`n`r`n"
    $hb=[Text.Encoding]::ASCII.GetBytes($h);$s.Write($hb,0,$hb.Length);$s.Write($body,0,$body.Length);$s.Flush()
}
function ApiError($s,$code,$msg,$detail){Send $s $code "application/json; charset=utf-8" (JsonBytes ([pscustomobject]@{ok=$false;error=[string]$msg;detail=[string]$detail}))}

function RunStateEngine{
    $eng=P "control\state\K01_STATE_ENGINE_v7.ps1"
    if(-not(Test-Path -LiteralPath $eng -PathType Leaf)){throw "State engine missing: $eng"}
    & $eng -RepoRoot $Repo | Out-Null
}
function State{
    RunStateEngine
    $s=ReadJsonPath (P "control\state\K01_STATE_CURRENT.json")
    return [pscustomobject]@{ok=$true;state=$s}
}
function Events{
    $p=P "control\state\K01_EVENT_LEDGER.jsonl";$ev=@()
    if(Test-Path -LiteralPath $p -PathType Leaf){
        foreach($line in Get-Content -LiteralPath $p -Encoding UTF8){
            if([string]::IsNullOrWhiteSpace($line)){continue}
            try{$ev+=($line|ConvertFrom-Json)}catch{}
        }
    }
    return [pscustomobject]@{ok=$true;events=@($ev|Select-Object -Last 100)}
}
function Dossier{
    return [pscustomobject]@{
        ok=$true
        dossier=ReadJsonPath (P "control\decision_system\K01_J2_C2R1_ENGINEERING_DOSSIER_v1.json")
        edr005=ReadJsonPath (P "control\decision_system\records\EDR-005_J2_COMPACT_FLANGE_v3.json")
        edr019=ReadJsonPath (P "control\decision_system\records\EDR-019_J2_PILOT_INNER_CLEARANCE_v1.json")
        workT03=ReadJsonPath (P "control\workpacks\K01_T03_PILOT_TOOL_WORKPACKAGE_v1.json")
        bom=ReadJsonPath (P "reports\bom\K01_BOM_RECONCILIATION_study_c2r1.json")
        drawingQa=ReadJsonPath (P "reports\cad\current\K01_DRAWING_QUALITY_P003_C2R1_v1.json")
        drawingV2=ReadJsonPath (P "reports\cad\current\K01_GATE04D_C2R1_TYPED_DRAWINGS_V2.json")
        gitClassification=ReadJsonPath (P "reports\git\K01_GIT_CLASSIFICATION_CURRENT.json")
    }
}
function Files{
    $r=@()
    foreach($e in $Registry.entries){$p=Resolve-Entry $e;$i=SafeInfo $p;$r+=[pscustomobject]@{id=$e.id;name=$e.name;domain=$e.domain;resolved=$i.path;exists=$i.exists;modified=$i.modified;bytes=$i.bytes}}
    return [pscustomobject]@{ok=$true;repo_root=$Repo;cad_root=$Cad;entries=$r}
}
function GitOut{param([string[]]$GitArgs);try{if(-not(Get-Command git -ErrorAction SilentlyContinue)){return "GIT_NOT_FOUND"};return (& git -C $Repo @GitArgs 2>&1|Out-String).Trim()}catch{return "ERROR: $($_.Exception.Message)"}}
function GitState{
    $st=GitOut @("status","--porcelain=v1");$ln=@();if($st -and -not $st.StartsWith("ERROR:") -and $st -ne "GIT_NOT_FOUND"){$ln=$st -split "`r?`n"}
    return [pscustomobject]@{ok=$true;branch=GitOut @("branch","--show-current");last_commit=GitOut @("log","-1","--format=%H|%cI|%s");origin=GitOut @("remote","get-url","origin");dirty_count=@($ln).Count;untracked_count=@($ln|Where-Object{$_.StartsWith("??")}).Count;status_lines=$ln}
}
function QueryId($t){if($t -match '[?&]id=([^&]+)'){return [uri]::UnescapeDataString($matches[1])};return ""}

$Actions=@{
 "RUN_C2R1_ALL"=P "cad_api\gates\gate04d_c2r1\00_GATE04D_C2R1_ALL.cmd"
 "RUN_R1_BOM"=P "cad_api\bom\RUN_K01_BOM_PIPELINE_C2R1.cmd"
 "RUN_R1_DRAWINGS_V2"=P "cad_api\gates\gate04d_c2r1\05_GATE04D_C2R1_DRAWINGS_V2.cmd"
 "RUN_GIT_CLASSIFY"=P "control\git\RUN_K01_GIT_CLASSIFY.cmd"
}
$Open=@{
 "OPEN_ROOTCAUSE"=P "reports\analysis\current\K01_C2_PILOT_INTERFERENCE_ROOT_CAUSE_v1.json"
 "OPEN_EDR019"=P "control\decision_system\records\EDR-019_J2_PILOT_INNER_CLEARANCE_v1.json"
 "OPEN_EDR005"=P "control\decision_system\records\EDR-005_J2_COMPACT_FLANGE_v3.json"
 "OPEN_MECH"=P "reports\analysis\current\K01_J2_C2_MECHANICAL_SCREEN_v1.json"
}

function AddFile($src,$dst,$cat,[ref]$m){
    if([string]::IsNullOrWhiteSpace($src) -or -not(Test-Path -LiteralPath $src -PathType Leaf)){return}
    $d=Join-Path $dst $cat;New-Item $d -ItemType Directory -Force|Out-Null
    $to=Join-Path $d ([IO.Path]::GetFileName($src));Copy-Item -LiteralPath $src -Destination $to -Force
    $m.Value+=[pscustomobject]@{category=$cat;name=[IO.Path]::GetFileName($src);source=$src;sha256=(Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash;modified=(Get-Item -LiteralPath $src).LastWriteTime.ToString("s")}
}
function Handoff{
    RunStateEngine
    $out=P "handoff\current";New-Item $out -ItemType Directory -Force|Out-Null
    $tmp=Join-Path $out "K01_AI_HANDOFF_CURRENT";if(Test-Path $tmp){Remove-Item $tmp -Recurse -Force};New-Item $tmp -ItemType Directory|Out-Null
    $m=@()
    foreach($e in $Registry.entries){
        if($e.id -eq "AI-HANDOFF"){continue}
        if($e.domain -in @("STATE","CONTROL","DECISION","CONFIGURATION","ANALYSIS","LIVE_REPORT","LIVE_LOG","BOM","DRAWING","GIT")){
            AddFile (Resolve-Entry $e) $tmp $e.domain ([ref]$m)
        }
    }
    foreach($rel in @("control\evidence\K01_SOURCE_REGISTRY_v1.json","control\system\K01_PART_IDENTITY_AUTHORITY_v1.json","docs\design\trade_studies\K01_J2_PILOT_INNER_CLEARANCE_TRADE_v1.json")){
        AddFile (P $rel) $tmp "CONTROL" ([ref]$m)
    }
    [pscustomobject]@{schema="k01_ai_handoff_manifest_v4";created=(Get-Date).ToString("o");active_design="Gate04D-C2R1";repo=$Repo;cad=$Cad;files=$m}|ConvertTo-Json -Depth 30|Set-Content (Join-Path $tmp "MANIFEST.json") -Encoding UTF8
    $zip=Join-Path $out "K01_AI_HANDOFF_CURRENT.zip";if(Test-Path $zip){Remove-Item $zip -Force};Compress-Archive -Path (Join-Path $tmp "*") -DestinationPath $zip -Force
    return $zip
}

$listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$Port);$listener.Start()
Write-Host "================================================================================";Write-Host "MARVILON K01 MEDTAS - Engineering Control Center v7";Write-Host "================================================================================";Write-Host "Repo: $Repo";Write-Host "CAD : $Cad";Write-Host "URL : http://127.0.0.1:$Port/"
Start-Process "http://127.0.0.1:$Port/"

while($true){
    $client=$listener.AcceptTcpClient();$target=""
    try{
        $stream=$client.GetStream();$reader=New-Object IO.StreamReader($stream,[Text.Encoding]::ASCII,$false,8192,$true)
        $rl=$reader.ReadLine();while(($line=$reader.ReadLine()) -ne $null -and $line -ne ""){}
        if(-not $rl){continue};$target=$rl.Split(" ")[1]
        if($target -eq "/" -or $target.StartsWith("/index")){Send $stream 200 "text/html; charset=utf-8" ([IO.File]::ReadAllBytes((Join-Path $Here "K01_Command_Center_v7.html")))}
        elseif($target.StartsWith("/api/state")){Send $stream 200 "application/json; charset=utf-8" (JsonBytes (State))}
        elseif($target.StartsWith("/api/events")){Send $stream 200 "application/json; charset=utf-8" (JsonBytes (Events))}
        elseif($target.StartsWith("/api/dossier")){Send $stream 200 "application/json; charset=utf-8" (JsonBytes (Dossier))}
        elseif($target.StartsWith("/api/files")){Send $stream 200 "application/json; charset=utf-8" (JsonBytes (Files))}
        elseif($target.StartsWith("/api/git")){Send $stream 200 "application/json; charset=utf-8" (JsonBytes (GitState))}
        elseif($target.StartsWith("/api/handoff/build")){$p=Handoff;Start-Process explorer.exe -ArgumentList "/select,`"$p`"";Send $stream 200 "application/json; charset=utf-8" (JsonBytes ([pscustomobject]@{ok=$true;path=$p}))}
        elseif($target.StartsWith("/api/action")){
            $id=QueryId $target
            if($Open.ContainsKey($id)){
                $p=$Open[$id];if(-not(Test-Path -LiteralPath $p -PathType Leaf)){ApiError $stream 404 "open target missing" $p;continue}
                Start-Process -FilePath $p;Send $stream 200 "application/json; charset=utf-8" (JsonBytes ([pscustomobject]@{ok=$true;path=$p}));continue
            }
            if(-not $Actions.ContainsKey($id)){ApiError $stream 404 "unknown action" $id;continue}
            $p=$Actions[$id];if(-not(Test-Path -LiteralPath $p -PathType Leaf)){ApiError $stream 404 "action file missing" $p;continue}
            Start-Process -FilePath "cmd.exe" -ArgumentList "/k","`"$p`"" -WorkingDirectory ([IO.Path]::GetDirectoryName($p))
            Send $stream 200 "application/json; charset=utf-8" (JsonBytes ([pscustomobject]@{ok=$true;action=$id;path=$p}))
        }
        elseif($target.StartsWith("/api/open") -or $target.StartsWith("/api/reveal")){
            $id=QueryId $target;$e=$Registry.entries|Where-Object{$_.id -eq $id}|Select-Object -First 1
            if(-not $e){ApiError $stream 404 "unknown file id" $id;continue}
            $p=Resolve-Entry $e;if([string]::IsNullOrWhiteSpace($p) -or -not(Test-Path -LiteralPath $p -PathType Leaf)){ApiError $stream 404 "file missing" $p;continue}
            if($target.StartsWith("/api/reveal")){Start-Process explorer.exe -ArgumentList "/select,`"$p`""}else{Start-Process -FilePath $p}
            Send $stream 200 "application/json; charset=utf-8" (JsonBytes ([pscustomobject]@{ok=$true;path=$p}))
        }else{Send $stream 404 "text/plain; charset=utf-8" (TextBytes "Not found")}
    }catch{
        try{if($target.StartsWith("/api/")){ApiError $stream 500 $_.Exception.Message $_.ScriptStackTrace}else{Send $stream 500 "text/plain; charset=utf-8" (TextBytes $_.Exception.Message)}}catch{}
    }finally{$client.Close()}
}
