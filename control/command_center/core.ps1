param(
    [string]$RepoRoot = "",
    [string]$CadRoot = "D:\Marvilon\K01\cad"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$script:RepoRoot = $RepoRoot
$script:CadRoot = $CadRoot

$registryPath = Join-Path $PSScriptRoot "data\file_registry.json"
if (-not (Test-Path -LiteralPath $registryPath -PathType Leaf)) {
    throw "File registry missing: $registryPath"
}
$script:Registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json

function Repo {
    param([string]$RelativePath)
    return (Join-Path $script:RepoRoot $RelativePath)
}

function RootFor {
    param([string]$RootName)
    if ($RootName -eq "cad") {
        return $script:CadRoot
    }
    return $script:RepoRoot
}

function ReadJson {
    param([string]$RelativePath)

    $path = Repo $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        return $null
    }

    try {
        return (Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json)
    }
    catch {
        return [pscustomobject]@{
            status = "PARSE_ERROR"
            path   = $path
            error  = $_.Exception.Message
        }
    }
}

function EntryValues {
    param(
        $Entry,
        [string]$PropertyName
    )

    $result = @()

    if ($null -eq $Entry) {
        return $result
    }

    if (-not ($Entry.PSObject.Properties.Name -contains $PropertyName)) {
        return $result
    }

    $raw = $Entry.$PropertyName
    if ($null -eq $raw) {
        return $result
    }

    foreach ($value in @($raw)) {
        if ($null -eq $value) {
            continue
        }

        $text = [string]$value
        if ([string]::IsNullOrWhiteSpace($text)) {
            continue
        }

        $result += $value
    }

    return $result
}

function ResolveEntry {
    param($Entry)

    $root = RootFor ([string]$Entry.root)
    $candidates = @(EntryValues $Entry "candidates")

    foreach ($relative in $candidates) {
        $path = Join-Path $root ([string]$relative)
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            return (Get-Item -LiteralPath $path).FullName
        }
    }

    $hits = @()
    $patterns = @(EntryValues $Entry "patterns")

    foreach ($pattern in $patterns) {
        try {
            $patternPath = Join-Path $root ([string]$pattern)
            $hits += @(Get-ChildItem -Path $patternPath -File -ErrorAction SilentlyContinue)
        }
        catch {
            # A malformed optional pattern must not kill the file registry.
        }
    }

    if ($hits.Count -gt 0) {
        $latest = $hits | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        return $latest.FullName
    }

    if ($candidates.Count -gt 0) {
        return (Join-Path $root ([string]$candidates[0]))
    }

    return ""
}

function GetFiles {
    $rows = @()

    foreach ($entry in @($script:Registry.entries)) {
        try {
            $path = ResolveEntry $entry
            $exists = $false

            if (-not [string]::IsNullOrWhiteSpace([string]$path)) {
                $exists = Test-Path -LiteralPath $path -PathType Leaf
            }

            $rows += [pscustomobject]@{
                id     = [string]$entry.id
                name   = [string]$entry.name
                domain = [string]$entry.domain
                path   = [string]$path
                exists = [bool]$exists
                error  = ""
            }
        }
        catch {
            $rows += [pscustomobject]@{
                id     = [string]$entry.id
                name   = [string]$entry.name
                domain = [string]$entry.domain
                path   = ""
                exists = $false
                error  = $_.Exception.Message
            }
        }
    }

    return [pscustomobject]@{
        status  = "PASS"
        entries = $rows
    }
}

function GitRun {
    param([string[]]$Arguments)

    try {
        $git = Get-Command git.exe -ErrorAction Stop
        $text = (& $git.Source -C $script:RepoRoot @Arguments 2>&1 | Out-String).Trim()

        return [pscustomobject]@{
            ok        = ($LASTEXITCODE -eq 0)
            text      = $text
            exit_code = $LASTEXITCODE
        }
    }
    catch {
        return [pscustomobject]@{
            ok        = $false
            text      = $_.Exception.Message
            exit_code = -1
        }
    }
}

function GetGit {
    $statusResult = GitRun @("status", "--porcelain=v1")
    $branchResult = GitRun @("branch", "--show-current")
    $lastResult   = GitRun @("log", "-1", "--format=%H|%cI|%s")
    $originResult = GitRun @("remote", "get-url", "origin")

    $lines = @()
    if ($statusResult.ok -and -not [string]::IsNullOrWhiteSpace($statusResult.text)) {
        $lines = @($statusResult.text -split "`r?`n")
    }

    $remoteHealth = ReadJson "reports\git\K01_GITHUB_REMOTE_HEALTH_CURRENT.json"

    return [pscustomobject]@{
        status        = $(if ($statusResult.ok) { "PASS_LOCAL_GIT" } else { "HOLD_GIT" })
        branch        = $branchResult.text
        dirty         = $lines.Count
        untracked     = @($lines | Where-Object { $_.StartsWith("??") }).Count
        last          = $lastResult.text
        origin        = $originResult.text
        remote_health = $remoteHealth
    }
}

function GetState {
    $reducer = Repo "control\state\reducer.ps1"

    if (Test-Path -LiteralPath $reducer -PathType Leaf) {
        & $reducer -RepoRoot $script:RepoRoot | Out-Null
        if ($LASTEXITCODE -ne 0) {
            return [pscustomobject]@{
                status = "STATE_REDUCER_FAILED"
                error  = "Reducer exit code $LASTEXITCODE"
            }
        }
    }

    $state = ReadJson "reports\control\K01_CURRENT_STATE.json"
    if ($null -eq $state) {
        return [pscustomobject]@{
            status = "STATE_MISSING"
        }
    }

    return $state
}

function GetBom {
    foreach ($relative in @(
        "bom\K01_BOM_NORMALIZED_CURRENT.json",
        "bom\K01_BOM_study_c2r1.json",
        "reports\bom\K01_BOM_RECONCILIATION_study_c2r1.json"
    )) {
        $value = ReadJson $relative
        if ($null -ne $value) {
            return $value
        }
    }

    return $null
}

function GetSolidWorksLive {
    return (ReadJson "reports\cad\live\K01_SOLIDWORKS_LIVE_STATE.json")
}
