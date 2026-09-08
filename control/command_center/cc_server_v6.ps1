$ErrorActionPreference="Stop"
$Here=$PSScriptRoot
$Repo=(Resolve-Path (Join-Path $Here "..\..")).Path
$Data=Join-Path $Here "data"
$Registry=Get-Content (Join-Path $Data "K01_FILE_REGISTRY_v6.json") -Raw -Encoding UTF8|ConvertFrom-Json
$Profiles=Get-Content (Join-Path $Data "K01_MACHINE_PROFILES_v2.json") -Raw -Encoding UTF8|ConvertFrom-Json
$Profile=$Profiles.profiles.($Profiles.active_profile)
$Cad=$Profile.cad_root
$Port=8765

function Root-For($n){ if($n -eq "cad"){return $Cad}; return $Repo }
function Values($e,$name){ if($e.PSObject.Properties.Name -contains $name){ return @($e.$name|Where-Object{$_}) }; return @() }

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

function Safe-Info($p){
    if([string]::IsNullOrWhiteSpace($p)){return [pscustomobject]@{path="";exists=$false;modified="";bytes=0}}
    try{
        if(Test-Path -LiteralPath $p -PathType Leaf){
            $i=Get-Item -LiteralPath $p
            return [pscustomobject]@{path=$p;exists=$true;modified=$i.LastWriteTime.ToString("s");bytes=$i.Length}
        }
    }catch{}
    return [pscustomobject]@{path=$p;exists=$false;modified="";bytes=0}
}

function JsonBytes($o){ [Text.Encoding]::UTF8.GetBytes(($o|ConvertTo-Json -Depth 40 -Compress)) }
function TextBytes($s){ [Text.Encoding]::UTF8.GetBytes([string]$s) }

function Send($s,$code,$type,[byte[]]$body){
    $st=if($code -eq 200){"OK"}elseif($code -eq 404){"Not Found"}else{"Error"}
    $h="HTTP/1.1 $code $st`r`nContent-Type: $type`r`nCache-Control: no-store`r`nContent-Length: $($body.Length)`r`nConnection: close`r`n`r`n"
    $hb=[Text.Encoding]::ASCII.GetBytes($h)
    $s.Write($hb,0,$hb.Length);$s.Write($body,0,$body.Length);$s.Flush()
}

function Send-ApiError($s,$code,$message,$detail){
    $o=[pscustomobject]@{ok=$false;error=[string]$message;detail=[string]$detail}
    Send $s $code "application/json; charset=utf-8" (JsonBytes $o)
}

function P($rel){ Join-Path $Repo $rel }

function ReadJson($p){
    if([string]::IsNullOrWhiteSpace($p) -or -not(Test-Path -LiteralPath $p -PathType Leaf)){return $null}
    try{return Get-Content -LiteralPath $p -Raw -Encoding UTF8|ConvertFrom-Json}
    catch{return [pscustomobject]@{status="PARSE_ERROR";error=$_.Exception.Message;path=$p}}
}

function Git-Out{param([string[]]$GitArgs)
    try{
        if(-not(Get-Command git -ErrorAction SilentlyContinue)){return "GIT_NOT_FOUND"}
        return (& git -C $Repo @GitArgs 2>&1|Out-String).Trim()
    }catch{return "ERROR: $($_.Exception.Message)"}
}
function Git-State{
    $st=Git-Out @("status","--porcelain=v1")
    $ln=@()
    if($st -and -not $st.StartsWith("ERROR:") -and $st -ne "GIT_NOT_FOUND"){$ln=$st -split "`r?`n"}
    return [pscustomobject]@{
        branch=Git-Out @("branch","--show-current")
        last_commit=Git-Out @("log","-1","--format=%H|%cI|%s")
        origin=Git-Out @("remote","get-url","origin")
        dirty_count=@($ln).Count
        untracked_count=@($ln|Where-Object{$_.StartsWith("??")}).Count
        status_lines=$ln
    }
}

function Artifact-State{
    $r=@()
    foreach($e in $Registry.entries){
        $resolved=Resolve-Entry $e
        $x=Safe-Info $resolved
        $r+=[pscustomobject]@{
            id=$e.id;name=$e.name;domain=$e.domain
            resolved=$x.path;exists=$x.exists;modified=$x.modified;bytes=$x.bytes
        }
    }
    return [pscustomobject]@{ok=$true;repo_root=$Repo;cad_root=$Cad;entries=$r}
}

function StatusOf($o,$fallback="OPEN"){
    if($null -eq $o){return $fallback}
    if($o.PSObject.Properties.Name -contains "status"){return [string]$o.status}
    return $fallback
}

function Current-State{
    $c2delta=ReadJson (P "reports\cad\current\K01_GATE04D_C2_INTERFERENCE_DELTA.json")
    $rootcause=ReadJson (P "reports\analysis\current\K01_C2_PILOT_INTERFERENCE_ROOT_CAUSE_v1.json")
    $r1build=ReadJson (P "reports\cad\current\K01_GATE04D_C2R1_TYPED_BUILD.json")
    $r1verify=ReadJson (P "reports\cad\current\K01_GATE04D_C2R1_VERIFY.json")
    $r1int=ReadJson (P "reports\cad\current\K01_GATE04D_C2R1_INTERFERENCE.json")
    $r1bom=ReadJson (P "bom\K01_BOM_RECONCILED_study_c2r1.json")
    $r1draw=ReadJson (P "reports\cad\current\K01_GATE04D_C2R1_TYPED_DRAWINGS.json")
    $mech=ReadJson (P "reports\analysis\current\K01_J2_C2_MECHANICAL_SCREEN_v1.json")
    $edr19=ReadJson (P "control\decision_system\records\EDR-019_J2_PILOT_INNER_CLEARANCE_v1.json")

    $r1all = if((StatusOf $r1build) -eq "PASS" -and (StatusOf $r1verify) -eq "PASS" -and (StatusOf $r1int) -eq "PASS"){"PASS"}else{"OPEN"}

    $tasks=@()
    $tasks += [pscustomobject]@{id="T01";name="C2 interference root cause";status=if((StatusOf $rootcause) -eq "ROOT_CAUSE_CONFIRMED"){"PASS"}else{"HOLD"};action="OPEN_ROOTCAUSE";kind="EVIDENCE";why="C2 rejected: exact pilot ID10.917 ↔ P006 head OD11.5 overlap is proven analytically and by CAD volume."}
    $tasks += [pscustomobject]@{id="T02";name="C2R1 build + verify + interference";status=$r1all;action="RUN_C2R1_ALL";kind="AUTOMATED";why="Active redesign: pilot ID12.00 study, OD14.10/L1.50 retained; must eliminate P003↔P006 collision without new interference."}
    $tasks += [pscustomobject]@{id="T03";name="Pilot tolerance + P006 service-tool envelope";status="OPEN";action="OPEN_EDR019";kind="ENGINEERING";why="Nominal radial clearance is 0.25 mm, but P006 head tolerance, pilot-ID tolerance and final tool access are not yet released."}
    $tasks += [pscustomobject]@{id="T04";name="O-ring compound + required clamp preload";status="OPEN";action="OPEN_EDR005";kind="ENGINEERING_INPUT";why="Gland geometry is controlled; compound/hardness and compression force must set minimum clamp load."}
    $tasks += [pscustomobject]@{id="T05";name="M2.5 joint + local flange/contact verification";status="OPEN";action="OPEN_MECH";kind="ANALYSIS";why="Thread screen does not reject M2.5, but release calculation needs actual preload/friction and local flange verification."}
    $tasks += [pscustomobject]@{id="T06";name="Thermal preload + service/galling closure";status="OPEN";action="OPEN_EDR005";kind="ENGINEERING";why="Repeated service and stainless fastener strategy must be released."}
    $tasks += [pscustomobject]@{id="T07";name="P007 static + buckling refresh";status="STALE";action="";kind="SOLVER";why="Refresh after C2R1 mechanical preload and geometry freeze."}
    $tasks += [pscustomobject]@{id="T08";name="C2R1 BOM reconciliation";status=StatusOf $r1bom;action="RUN_R1_BOM";kind="AUTOMATED";why="Generate after R1 assembly exists; CAD quantity + controlled identity/material state."}
    $tasks += [pscustomobject]@{id="T09";name="C2R1 draft drawings";status=StatusOf $r1draw;action="RUN_R1_DRAWINGS";kind="AUTOMATED";why="Draft only; production release remains blocked until EDS gates pass."}
    $tasks += [pscustomobject]@{id="T10";name="Final FEMM impact/release model";status="OPEN";action="";kind="SOLVER";why="Run after J2 mechanical freeze and P015/B001 production data freeze."}
    $tasks += [pscustomobject]@{id="T11";name="Atomic production promotion";status="HOLD";action="";kind="RELEASE";why="P003/P007 promote together only after all mandatory gates pass."}

    $next=$tasks|Where-Object{$_.status -notmatch "^(PASS|SCREEN_PASS)"}|Select-Object -First 1

    return [pscustomobject]@{
        ok=$true
        active_design="Gate04D-C2R1"
        c2_delta=$c2delta
        root_cause=$rootcause
        r1_build=$r1build
        r1_verify=$r1verify
        r1_interference=$r1int
        r1_bom=$r1bom
        r1_drawings=$r1draw
        mechanical=$mech
        edr019=$edr19
        tasks=$tasks
        next_task=$next
    }
}

function QueryId($t){
    if($t -match '[?&]id=([^&]+)'){return [uri]::UnescapeDataString($matches[1])}
    return ""
}

$Actions=@{
    "RUN_C2R1_ALL"=P "cad_api\gates\gate04d_c2r1\00_GATE04D_C2R1_ALL.cmd"
    "RUN_R1_BOM"=P "cad_api\bom\RUN_K01_BOM_PIPELINE_C2R1.cmd"
    "RUN_R1_DRAWINGS"=P "cad_api\gates\gate04d_c2r1\04_GATE04D_C2R1_DRAFT_DRAWINGS.cmd"
}
$OpenActions=@{
    "OPEN_ROOTCAUSE"=P "reports\analysis\current\K01_C2_PILOT_INTERFERENCE_ROOT_CAUSE_v1.json"
    "OPEN_EDR019"=P "control\decision_system\records\EDR-019_J2_PILOT_INNER_CLEARANCE_v1.json"
    "OPEN_EDR005"=P "control\decision_system\records\EDR-005_J2_COMPACT_FLANGE_v3.json"
    "OPEN_MECH"=P "reports\analysis\current\K01_J2_C2_MECHANICAL_SCREEN_v1.json"
}

function AddFile($src,$dst,$cat,[ref]$manifest){
    if([string]::IsNullOrWhiteSpace($src) -or -not(Test-Path -LiteralPath $src -PathType Leaf)){return}
    $d=Join-Path $dst $cat;New-Item $d -ItemType Directory -Force|Out-Null
    $to=Join-Path $d ([IO.Path]::GetFileName($src));Copy-Item -LiteralPath $src -Destination $to -Force
    $manifest.Value+=[pscustomobject]@{category=$cat;name=[IO.Path]::GetFileName($src);source=$src;sha256=(Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash;modified=(Get-Item -LiteralPath $src).LastWriteTime.ToString("s")}
}

function BuildHandoff{
    $out=P "handoff\current";New-Item $out -ItemType Directory -Force|Out-Null
    $tmp=Join-Path $out "K01_AI_HANDOFF_CURRENT"
    if(Test-Path $tmp){Remove-Item $tmp -Recurse -Force}
    New-Item $tmp -ItemType Directory|Out-Null
    $m=@()
    foreach($e in $Registry.entries){
        if($e.id -eq "AI-HANDOFF"){continue}
        if($e.domain -in @("CONTROL","DECISION","CONFIGURATION","HISTORY","ANALYSIS","LIVE_REPORT","LIVE_LOG","BOM","DRAWING")){
            AddFile (Resolve-Entry $e) $tmp $e.domain ([ref]$m)
        }
    }
    foreach($rel in @(
        "control\evidence\K01_SOURCE_REGISTRY_v1.json",
        "control\system\K01_PART_IDENTITY_AUTHORITY_v1.json",
        "docs\design\trade_studies\K01_J2_PILOT_INNER_CLEARANCE_TRADE_v1.json"
    )){AddFile (P $rel) $tmp "CONTROL" ([ref]$m)}
    [pscustomobject]@{schema="k01_ai_handoff_manifest_v3";created=(Get-Date).ToString("o");active_design="Gate04D-C2R1";repo=$Repo;cad=$Cad;files=$m}|ConvertTo-Json -Depth 30|Set-Content (Join-Path $tmp "MANIFEST.json") -Encoding UTF8
    $zip=Join-Path $out "K01_AI_HANDOFF_CURRENT.zip"
    if(Test-Path $zip){Remove-Item $zip -Force}
    Compress-Archive -Path (Join-Path $tmp "*") -DestinationPath $zip -Force
    return $zip
}

$listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$Port)
$listener.Start()
Write-Host "================================================================================"
Write-Host "MARVILON K01 MEDTAS - Engineering Control Center v6"
Write-Host "================================================================================"
Write-Host "Repo: $Repo";Write-Host "CAD : $Cad";Write-Host "URL : http://127.0.0.1:$Port/"
Start-Process "http://127.0.0.1:$Port/"

while($true){
    $client=$listener.AcceptTcpClient()
    $target=""
    try{
        $stream=$client.GetStream()
        $reader=New-Object IO.StreamReader($stream,[Text.Encoding]::ASCII,$false,8192,$true)
        $rl=$reader.ReadLine()
        while(($line=$reader.ReadLine()) -ne $null -and $line -ne ""){}
        if(-not $rl){continue}
        $target=$rl.Split(" ")[1]

        if($target -eq "/" -or $target.StartsWith("/index")){
            Send $stream 200 "text/html; charset=utf-8" ([IO.File]::ReadAllBytes((Join-Path $Here "K01_Command_Center_v6.html")))
        }
        elseif($target.StartsWith("/api/state")){
            Send $stream 200 "application/json; charset=utf-8" (JsonBytes (Current-State))
        }
        elseif($target.StartsWith("/api/files")){
            Send $stream 200 "application/json; charset=utf-8" (JsonBytes (Artifact-State))
        }
        elseif($target.StartsWith("/api/git")){
            Send $stream 200 "application/json; charset=utf-8" (JsonBytes ([pscustomobject]@{ok=$true;git=(Git-State)}))
        }
        elseif($target.StartsWith("/api/handoff/build")){
            $p=BuildHandoff
            Start-Process explorer.exe -ArgumentList "/select,`"$p`""
            Send $stream 200 "application/json; charset=utf-8" (JsonBytes ([pscustomobject]@{ok=$true;path=$p}))
        }
        elseif($target.StartsWith("/api/action")){
            $id=QueryId $target
            if($OpenActions.ContainsKey($id)){
                $p=$OpenActions[$id]
                if(-not(Test-Path -LiteralPath $p -PathType Leaf)){Send-ApiError $stream 404 "open target missing" $p;continue}
                Start-Process -FilePath $p
                Send $stream 200 "application/json; charset=utf-8" (JsonBytes ([pscustomobject]@{ok=$true;path=$p}))
                continue
            }
            if(-not $Actions.ContainsKey($id)){Send-ApiError $stream 404 "unknown action" $id;continue}
            $p=$Actions[$id]
            if(-not(Test-Path -LiteralPath $p -PathType Leaf)){Send-ApiError $stream 404 "action file missing" $p;continue}
            Start-Process -FilePath "cmd.exe" -ArgumentList "/k","`"$p`"" -WorkingDirectory ([IO.Path]::GetDirectoryName($p))
            Send $stream 200 "application/json; charset=utf-8" (JsonBytes ([pscustomobject]@{ok=$true;action=$id;path=$p}))
        }
        elseif($target.StartsWith("/api/open") -or $target.StartsWith("/api/reveal")){
            $id=QueryId $target
            $e=$Registry.entries|Where-Object{$_.id -eq $id}|Select-Object -First 1
            if(-not $e){Send-ApiError $stream 404 "unknown file id" $id;continue}
            $p=Resolve-Entry $e
            if([string]::IsNullOrWhiteSpace($p) -or -not(Test-Path -LiteralPath $p -PathType Leaf)){Send-ApiError $stream 404 "file missing" $p;continue}
            if($target.StartsWith("/api/reveal")){Start-Process explorer.exe -ArgumentList "/select,`"$p`""}else{Start-Process -FilePath $p}
            Send $stream 200 "application/json; charset=utf-8" (JsonBytes ([pscustomobject]@{ok=$true;path=$p}))
        }
        else{
            Send $stream 404 "text/plain; charset=utf-8" (TextBytes "Not found")
        }
    }
    catch{
        try{
            if($target.StartsWith("/api/")){Send-ApiError $stream 500 $_.Exception.Message $_.ScriptStackTrace}
            else{Send $stream 500 "text/plain; charset=utf-8" (TextBytes $_.Exception.Message)}
        }catch{}
    }
    finally{$client.Close()}
}
