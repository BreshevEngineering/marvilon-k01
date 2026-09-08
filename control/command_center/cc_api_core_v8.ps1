param(
    [string]$RepoRoot="",
    [string]$CadRoot="D:\Marvilon\K01\cad"
)

$ErrorActionPreference='Stop'

if([string]::IsNullOrWhiteSpace($RepoRoot)){
    $RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$script:MEDTAS_REPO=$RepoRoot
$script:MEDTAS_CAD=$CadRoot
$script:MEDTAS_REGISTRY_PATH=Join-Path $PSScriptRoot "data\K01_FILE_REGISTRY_v8.json"

if(-not(Test-Path -LiteralPath $script:MEDTAS_REGISTRY_PATH -PathType Leaf)){
    throw "File registry missing: $script:MEDTAS_REGISTRY_PATH"
}

$script:MEDTAS_REGISTRY=Get-Content -LiteralPath $script:MEDTAS_REGISTRY_PATH -Raw -Encoding UTF8 | ConvertFrom-Json

function Get-MedtasRepoPath([string]$RelativePath){
    return (Join-Path $script:MEDTAS_REPO $RelativePath)
}

function Read-MedtasJson([string]$RelativePath){
    $p=Get-MedtasRepoPath $RelativePath
    if(-not(Test-Path -LiteralPath $p -PathType Leaf)){ return $null }
    try{
        return (Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json)
    }catch{
        return [pscustomobject]@{
            status='PARSE_ERROR'
            path=$p
            error=$_.Exception.Message
        }
    }
}

function Get-MedtasEntryValues($Entry,[string]$Name){
    if($null -eq $Entry){ return @() }
    if(-not($Entry.PSObject.Properties.Name -contains $Name)){ return @() }
    $v=$Entry.$Name
    if($null -eq $v){ return @() }
    return @($v | Where-Object{
        $_ -ne $null -and -not [string]::IsNullOrWhiteSpace([string]$_)
    })
}

function Get-MedtasRoot([string]$RootName){
    if($RootName -eq 'cad'){ return $script:MEDTAS_CAD }
    return $script:MEDTAS_REPO
}

function Resolve-MedtasEntry($Entry){
    $root=Get-MedtasRoot ([string]$Entry.root)
    $candidates=Get-MedtasEntryValues $Entry 'candidates'

    foreach($rel in $candidates){
        try{
            $p=Join-Path $root ([string]$rel)
            if(Test-Path -LiteralPath $p -PathType Leaf){
                return (Get-Item -LiteralPath $p).FullName
            }
        }catch{}
    }

    $hits=@()
    foreach($pattern in (Get-MedtasEntryValues $Entry 'patterns')){
        try{
            $hits += @(Get-ChildItem -Path (Join-Path $root ([string]$pattern)) -File -ErrorAction SilentlyContinue)
        }catch{}
    }
    if($hits.Count -gt 0){
        return ($hits | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
    }

    if($candidates.Count -gt 0){
        try{ return (Join-Path $root ([string]$candidates[0])) }catch{}
    }
    return ''
}

function Get-MedtasFilesState(){
    $rows=@()
    foreach($entry in @($script:MEDTAS_REGISTRY.entries)){
        try{
            $resolved=Resolve-MedtasEntry $entry
            $exists=$false
            if(-not [string]::IsNullOrWhiteSpace([string]$resolved)){
                $exists=Test-Path -LiteralPath $resolved -PathType Leaf
            }
            $rows += [pscustomobject]@{
                id=[string]$entry.id
                name=[string]$entry.name
                domain=[string]$entry.domain
                path=[string]$resolved
                exists=[bool]$exists
                modified=if($exists){(Get-Item -LiteralPath $resolved).LastWriteTime.ToString('s')}else{''}
                error=''
            }
        }catch{
            $rows += [pscustomobject]@{
                id=[string]$entry.id
                name=[string]$entry.name
                domain=[string]$entry.domain
                path=''
                exists=$false
                modified=''
                error=$_.Exception.Message
            }
        }
    }

    return [pscustomobject]@{
        status='PASS'
        repo_root=$script:MEDTAS_REPO
        cad_root=$script:MEDTAS_CAD
        entries=$rows
    }
}

function Invoke-MedtasGit([string[]]$GitArgs){
    try{
        $git=Get-Command git.exe -ErrorAction Stop
        $text=(& $git.Source -C $script:MEDTAS_REPO @GitArgs 2>&1 | Out-String).Trim()
        return [pscustomobject]@{
            ok=($LASTEXITCODE -eq 0)
            text=$text
            exit_code=$LASTEXITCODE
        }
    }catch{
        return [pscustomobject]@{
            ok=$false
            text=$_.Exception.Message
            exit_code=-1
        }
    }
}

function Get-MedtasGitState(){
    $statusResult=Invoke-MedtasGit @('status','--porcelain=v1')
    $branchResult=Invoke-MedtasGit @('branch','--show-current')
    $lastResult=Invoke-MedtasGit @('log','-1','--format=%H|%cI|%s')
    $originResult=Invoke-MedtasGit @('remote','get-url','origin')

    $lines=@()
    if($statusResult.ok -and -not [string]::IsNullOrWhiteSpace($statusResult.text)){
        $lines=@($statusResult.text -split "`r?`n")
    }

    return [pscustomobject]@{
        status=if($statusResult.ok){'PASS_LOCAL_GIT'}else{'HOLD_GIT_UNAVAILABLE'}
        branch=$branchResult.text
        dirty=$lines.Count
        untracked=@($lines | Where-Object{$_.StartsWith('??')}).Count
        last=$lastResult.text
        origin=$originResult.text
        classification=(Read-MedtasJson 'reports\git\K01_GIT_CLASSIFICATION_CURRENT.json')
        remote_health=(Read-MedtasJson 'reports\git\K01_GITHUB_REMOTE_HEALTH_CURRENT.json')
        command_errors=@(
            if(-not $statusResult.ok){"status: "+$statusResult.text}
            if(-not $branchResult.ok){"branch: "+$branchResult.text}
            if(-not $lastResult.ok){"log: "+$lastResult.text}
            if(-not $originResult.ok){"origin: "+$originResult.text}
        )
    }
}

function Get-MedtasEvents(){
    $p=Get-MedtasRepoPath 'control\state\K01_EVENT_LEDGER_v8.jsonl'
    $events=@()
    if(Test-Path -LiteralPath $p -PathType Leaf){
        foreach($line in Get-Content -LiteralPath $p -Encoding UTF8){
            if([string]::IsNullOrWhiteSpace($line)){ continue }
            try{ $events += ($line | ConvertFrom-Json) }catch{}
        }
    }
    return @($events | Select-Object -Last 100)
}

function Get-MedtasState([bool]$Refresh=$true){
    if($Refresh){
        $engine=Get-MedtasRepoPath 'control\state\K01_STATE_ENGINE_v8.ps1'
        if(Test-Path -LiteralPath $engine -PathType Leaf){
            try{ & $engine -RepoRoot $script:MEDTAS_REPO | Out-Null }
            catch{
                return [pscustomobject]@{
                    schema='k01_state_error'
                    status='STATE_ENGINE_ERROR'
                    error=$_.Exception.Message
                }
            }
        }
    }
    $s=Read-MedtasJson 'control\state\K01_STATE_CURRENT_v8.json'
    if($null -eq $s){
        return [pscustomobject]@{
            schema='k01_state_missing'
            status='STATE_NOT_BUILT'
        }
    }
    return $s
}

function Test-MedtasApiCore(){
    $results=@()

    foreach($name in @('state','git','files','events')){
        try{
            $value=$null
            switch($name){
                'state' {$value=Get-MedtasState $false}
                'git'   {$value=Get-MedtasGitState}
                'files' {$value=Get-MedtasFilesState}
                'events'{$value=@(Get-MedtasEvents)}
            }
            # The same serialization path used by HTTP responses.
            $json=$value | ConvertTo-Json -Depth 50 -Compress
            $results += [pscustomobject]@{
                subsystem=$name
                status='PASS'
                bytes=[Text.Encoding]::UTF8.GetByteCount($json)
                error=''
            }
        }catch{
            $results += [pscustomobject]@{
                subsystem=$name
                status='FAIL'
                bytes=0
                error=$_.Exception.Message
            }
        }
    }

    $fail=@($results | Where-Object{$_.status -ne 'PASS'}).Count
    return [pscustomobject]@{
        schema='k01_command_center_core_selftest_v1'
        created=(Get-Date).ToString('o')
        status=if($fail -eq 0){'PASS_API_CONTRACT'}else{'HOLD_API_CONTRACT'}
        failures=$fail
        results=$results
    }
}
