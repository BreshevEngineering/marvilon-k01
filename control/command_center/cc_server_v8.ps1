param([int]$Port=8765)
$ErrorActionPreference='Stop'

$Here=$PSScriptRoot
$Repo=(Resolve-Path (Join-Path $Here "..\..")).Path

. (Join-Path $Here 'cc_api_core_v8.ps1') -RepoRoot $Repo

function Convert-MedtasBytes($Object){
    $json=$Object | ConvertTo-Json -Depth 50 -Compress
    return [Text.Encoding]::UTF8.GetBytes($json)
}

function Convert-MedtasTextBytes([string]$Text){
    return [Text.Encoding]::UTF8.GetBytes($Text)
}

function Get-HttpReason([int]$Code){
    switch($Code){
        200 {return 'OK'}
        404 {return 'Not Found'}
        500 {return 'Internal Server Error'}
        default {return 'Response'}
    }
}

function Send-HttpResponse($Stream,[int]$Code,[string]$ContentType,[byte[]]$Body){
    $reason=Get-HttpReason $Code
    $header="HTTP/1.1 $Code $reason`r`nContent-Type: $ContentType`r`nCache-Control: no-store`r`nContent-Length: $($Body.Length)`r`nConnection: close`r`n`r`n"
    $headerBytes=[Text.Encoding]::ASCII.GetBytes($header)
    $Stream.Write($headerBytes,0,$headerBytes.Length)
    $Stream.Write($Body,0,$Body.Length)
    $Stream.Flush()
}

function Get-QueryId([string]$Target){
    if($Target -match '[?&]id=([^&]+)'){
        return [uri]::UnescapeDataString($matches[1])
    }
    return ''
}

function Get-MedtasActionMap(){
    return @{
        'RUN_C2R1_ALL'       = Get-MedtasRepoPath 'cad_api\gates\gate04d_c2r1\00_GATE04D_C2R1_ALL.cmd'
        'RUN_P006_SERVICE'    = Get-MedtasRepoPath 'cad_api\gates\gate04e_p006_service\RUN_GATE04E_P006_SERVICE_BUILD.cmd'
        'RUN_DRAW_LINT'       = Get-MedtasRepoPath 'control\drawings\RUN_K01_DRAWING_INTENT_LINT.cmd'
        'RUN_DRAW_VISUAL'     = Get-MedtasRepoPath 'control\drawings\RUN_K01_DRAWING_VISUAL_APPROVAL.cmd'
        'RUN_DRAW_V3'         = Get-MedtasRepoPath 'cad_api\gates\gate04d_c2r1\06_GATE04D_C2R1_DRAWINGS_V3.cmd'
        'RUN_BOM_DRY'         = Get-MedtasRepoPath 'cad_api\bom\03_BOM_PROPERTY_PROJECTION_DRY_RUN.cmd'
        'RUN_BOM_APPLY'       = Get-MedtasRepoPath 'cad_api\bom\04_BOM_PROPERTY_PROJECTION_APPLY.cmd'
        'RUN_GIT_V2'          = Get-MedtasRepoPath 'control\git\RUN_K01_GIT_CLASSIFY_V2.cmd'
        'START_SW_BRIDGE'     = Get-MedtasRepoPath 'cad_api\bridge\START_K01_SOLIDWORKS_LIVE_BRIDGE.cmd'
        'CHECK_FEMM_INSTALL'  = Get-MedtasRepoPath 'control\femm\CHECK_K01_FEMM_INSTALL.cmd'
        'CHECK_GITHUB_REMOTE' = Get-MedtasRepoPath 'control\git\CHECK_K01_GITHUB_REMOTE.cmd'
        'RUN_CC_SELFTEST'      = Join-Path $Here 'RUN_K01_COMMAND_CENTER_SELFTEST.cmd'
    }
}

function Get-MedtasOpenMap(){
    return @{
        'OPEN_WP_T04'  = Get-MedtasRepoPath 'control\workpacks\K01_T04_SEAL_PRELOAD_WORKPACKAGE_v1.json'
        'OPEN_WP_T05'  = Get-MedtasRepoPath 'control\workpacks\K01_T05_J2_CLAMP_STRENGTH_WORKPACKAGE_v1.json'
        'OPEN_WP_T06'  = Get-MedtasRepoPath 'control\workpacks\K01_T06_THERMAL_GALLING_SERVICE_WORKPACKAGE_v1.json'
        'OPEN_WP_T07'  = Get-MedtasRepoPath 'control\workpacks\K01_T07_P007_STRUCTURAL_REFRESH_v1.json'
        'OPEN_WP_T09'  = Get-MedtasRepoPath 'control\workpacks\K01_T09_DRAWING_TPD_RELEASE_v1.json'
        'OPEN_WP_T10'  = Get-MedtasRepoPath 'control\workpacks\K01_T10_FEMM_BENCH_RELEASE_v1.json'
        'OPEN_FILTER'   = Get-MedtasRepoPath 'control\technical_filter\K01_J2_C2R1_TECHNICAL_FILTER_v1.json'
        'OPEN_DT_ARCH'  = Get-MedtasRepoPath 'control\digital_thread\K01_MEDTAS_DIGITAL_THREAD_ARCHITECTURE_v2.json'
    }
}

function Build-MedtasHandoff(){
    [void](Get-MedtasState $true)

    $out=Get-MedtasRepoPath 'handoff\current'
    New-Item -Path $out -ItemType Directory -Force | Out-Null

    $tmp=Join-Path $out 'K01_AI_HANDOFF_V8'
    if(Test-Path -LiteralPath $tmp){Remove-Item -LiteralPath $tmp -Recurse -Force}
    New-Item -Path $tmp -ItemType Directory -Force | Out-Null

    $relativeFiles=@(
        'control\state\K01_STATE_CURRENT_v8.json',
        'control\state\K01_EVENT_LEDGER_v8.jsonl',
        'control\release\K01_J2_C2R1_PRODUCTION_RELEASE_PACKAGE_v1.json',
        'control\decision_system\K01_J2_C2R1_ENGINEERING_DOSSIER_v2.json',
        'control\technical_filter\K01_J2_C2R1_TECHNICAL_FILTER_v1.json',
        'control\digital_thread\K01_MEDTAS_DIGITAL_THREAD_ARCHITECTURE_v2.json',
        'control\drawings\K01_TPD_DRAWING_ASSURANCE_STANDARD_v1.json',
        'control\evidence\K01_SOURCE_REGISTRY_v2.json',
        'control\workpacks\K01_T03_PILOT_TOOL_WORKPACKAGE_v2.json',
        'control\workpacks\K01_T04_SEAL_PRELOAD_WORKPACKAGE_v1.json',
        'control\workpacks\K01_T04_MEDIA_ENVELOPE_v1.json',
        'control\workpacks\K01_T05_J2_CLAMP_STRENGTH_WORKPACKAGE_v1.json',
        'control\workpacks\K01_T06_THERMAL_GALLING_SERVICE_WORKPACKAGE_v1.json',
        'control\workpacks\K01_T07_P007_STRUCTURAL_REFRESH_v1.json',
        'control\workpacks\K01_T08_BOM_PROPERTY_PROJECTION_v1.json',
        'control\workpacks\K01_T09_DRAWING_TPD_RELEASE_v1.json',
        'control\workpacks\K01_T10_FEMM_BENCH_RELEASE_v1.json',
        'reports\cad\current\K01_GATE04D_C2R1_TYPED_BUILD.json',
        'reports\cad\current\K01_GATE04D_C2R1_VERIFY.json',
        'reports\cad\current\K01_GATE04D_C2R1_INTERFERENCE.json',
        'reports\cad\current\K01_GATE04E_P006_SERVICE_BUILD.json',
        'reports\cad\current\K01_GATE04E_P006_SERVICE_VERIFY.json',
        'reports\bom\K01_BOM_RECONCILIATION_study_c2r1.json',
        'reports\femm\K01_FEMM_INSTALL_CURRENT.json',
        'reports\git\K01_GIT_CLASSIFICATION_CURRENT.json',
        'reports\git\K01_GITHUB_REMOTE_HEALTH_CURRENT.json'
    )

    foreach($relative in $relativeFiles){
        $source=Get-MedtasRepoPath $relative
        if(-not(Test-Path -LiteralPath $source -PathType Leaf)){continue}

        $destination=Join-Path $tmp $relative
        New-Item -Path ([IO.Path]::GetDirectoryName($destination)) -ItemType Directory -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }

    $zip=Join-Path $out 'K01_AI_HANDOFF_CURRENT.zip'
    if(Test-Path -LiteralPath $zip){Remove-Item -LiteralPath $zip -Force}
    Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath $zip -Force
    return $zip
}

# Startup contract self-test. Failure is logged but Git/files degradation no longer prevents the server from starting.
$selfTest=Test-MedtasApiCore
Write-Host "================================================================================"
Write-Host "MARVILON K01 MEDTAS v8.4"
Write-Host "================================================================================"
Write-Host "API core self-test: $($selfTest.status)"
foreach($x in $selfTest.results){
    Write-Host ("  {0,-8} {1,-5} {2}" -f $x.subsystem,$x.status,$x.error)
}

$listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$Port)
$listener.Start()

Write-Host "Repo: $script:MEDTAS_REPO"
Write-Host "CAD : $script:MEDTAS_CAD"
Write-Host "URL : http://127.0.0.1:$Port/"
Start-Process "http://127.0.0.1:$Port/"

$actions=Get-MedtasActionMap
$openMap=Get-MedtasOpenMap

while($true){
    $client=$listener.AcceptTcpClient()
    $stream=$null
    $target=''

    try{
        $stream=$client.GetStream()
        $reader=New-Object IO.StreamReader($stream,[Text.Encoding]::ASCII,$false,8192,$true)

        $requestLine=$reader.ReadLine()
        while(($line=$reader.ReadLine()) -ne $null -and $line -ne ''){}

        if([string]::IsNullOrWhiteSpace($requestLine)){continue}
        $parts=$requestLine.Split(' ')
        if($parts.Count -lt 2){continue}
        $target=$parts[1]

        if($target -eq '/' -or $target.StartsWith('/index')){
            Send-HttpResponse $stream 200 'text/html; charset=utf-8' ([IO.File]::ReadAllBytes((Join-Path $Here 'K01_Command_Center_v8.html')))
            continue
        }

        if($target.StartsWith('/api/state')){
            $payload=[pscustomobject]@{ok=$true;state=(Get-MedtasState $true)}
            Send-HttpResponse $stream 200 'application/json; charset=utf-8' (Convert-MedtasBytes $payload)
            continue
        }

        if($target.StartsWith('/api/git')){
            $payload=[pscustomobject]@{ok=$true;git=(Get-MedtasGitState)}
            Send-HttpResponse $stream 200 'application/json; charset=utf-8' (Convert-MedtasBytes $payload)
            continue
        }

        if($target.StartsWith('/api/files')){
            $payload=[pscustomobject]@{ok=$true;files=(Get-MedtasFilesState)}
            Send-HttpResponse $stream 200 'application/json; charset=utf-8' (Convert-MedtasBytes $payload)
            continue
        }

        if($target.StartsWith('/api/events')){
            $payload=[pscustomobject]@{ok=$true;events=@(Get-MedtasEvents)}
            Send-HttpResponse $stream 200 'application/json; charset=utf-8' (Convert-MedtasBytes $payload)
            continue
        }

        if($target.StartsWith('/api/health')){
            $payload=[pscustomobject]@{ok=$true;health=(Test-MedtasApiCore)}
            Send-HttpResponse $stream 200 'application/json; charset=utf-8' (Convert-MedtasBytes $payload)
            continue
        }

        if($target.StartsWith('/api/open') -or $target.StartsWith('/api/reveal')){
            $id=Get-QueryId $target
            $entry=$script:MEDTAS_REGISTRY.entries | Where-Object{$_.id -eq $id} | Select-Object -First 1

            if($null -eq $entry){
                Send-HttpResponse $stream 404 'application/json; charset=utf-8' (Convert-MedtasBytes ([pscustomobject]@{ok=$false;error='unknown file id'}))
                continue
            }

            $resolved=Resolve-MedtasEntry $entry
            if([string]::IsNullOrWhiteSpace([string]$resolved) -or -not(Test-Path -LiteralPath $resolved -PathType Leaf)){
                Send-HttpResponse $stream 404 'application/json; charset=utf-8' (Convert-MedtasBytes ([pscustomobject]@{ok=$false;error='file missing';path=$resolved}))
                continue
            }

            if($target.StartsWith('/api/reveal')){
                Start-Process explorer.exe -ArgumentList "/select,`"$resolved`""
            }else{
                Start-Process -FilePath $resolved
            }

            Send-HttpResponse $stream 200 'application/json; charset=utf-8' (Convert-MedtasBytes ([pscustomobject]@{ok=$true;path=$resolved}))
            continue
        }

        if($target.StartsWith('/api/action')){
            $id=Get-QueryId $target

            if($actions.ContainsKey($id)){
                $path=[string]$actions[$id]
                if(-not(Test-Path -LiteralPath $path -PathType Leaf)){
                    Send-HttpResponse $stream 404 'application/json; charset=utf-8' (Convert-MedtasBytes ([pscustomobject]@{ok=$false;error='action file missing';path=$path}))
                    continue
                }
                Start-Process -FilePath 'cmd.exe' -ArgumentList '/k',("`"$path`"") -WorkingDirectory ([IO.Path]::GetDirectoryName($path))
                Send-HttpResponse $stream 200 'application/json; charset=utf-8' (Convert-MedtasBytes ([pscustomobject]@{ok=$true;id=$id;path=$path}))
                continue
            }

            if($openMap.ContainsKey($id)){
                $path=[string]$openMap[$id]
                if(-not(Test-Path -LiteralPath $path -PathType Leaf)){
                    Send-HttpResponse $stream 404 'application/json; charset=utf-8' (Convert-MedtasBytes ([pscustomobject]@{ok=$false;error='open target missing';path=$path}))
                    continue
                }
                Start-Process -FilePath $path
                Send-HttpResponse $stream 200 'application/json; charset=utf-8' (Convert-MedtasBytes ([pscustomobject]@{ok=$true;id=$id;path=$path}))
                continue
            }

            Send-HttpResponse $stream 404 'application/json; charset=utf-8' (Convert-MedtasBytes ([pscustomobject]@{ok=$false;error='unknown action';id=$id}))
            continue
        }

        if($target.StartsWith('/api/handoff')){
            $zip=Build-MedtasHandoff
            Start-Process explorer.exe -ArgumentList "/select,`"$zip`""
            Send-HttpResponse $stream 200 'application/json; charset=utf-8' (Convert-MedtasBytes ([pscustomobject]@{ok=$true;path=$zip}))
            continue
        }

        Send-HttpResponse $stream 404 'text/plain; charset=utf-8' (Convert-MedtasTextBytes 'not found')
    }
    catch{
        if($null -ne $stream){
            try{
                $payload=[pscustomobject]@{
                    ok=$false
                    endpoint=$target
                    error=$_.Exception.Message
                }
                Send-HttpResponse $stream 500 'application/json; charset=utf-8' (Convert-MedtasBytes $payload)
            }catch{}
        }
    }
    finally{
        $client.Close()
    }
}
