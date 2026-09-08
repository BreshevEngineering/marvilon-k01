$ErrorActionPreference = "Stop"

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

& (Join-Path $PSScriptRoot "run_reducer_tests.ps1")
if ($LASTEXITCODE -ne 0) {
    exit 2
}

. (Join-Path $repo "control\command_center\core.ps1") -RepoRoot $repo

$checks = @()

try {
    $state = GetState
    $json = $state | ConvertTo-Json -Depth 60 -Compress
    $checks += [pscustomobject]@{
        name   = "state"
        status = "PASS"
        bytes  = [Text.Encoding]::UTF8.GetByteCount($json)
        error  = ""
    }
}
catch {
    $checks += [pscustomobject]@{
        name   = "state"
        status = "FAIL"
        bytes  = 0
        error  = $_.Exception.Message
    }
}

try {
    $files = GetFiles
    $json = $files | ConvertTo-Json -Depth 60 -Compress
    $checks += [pscustomobject]@{
        name   = "files"
        status = "PASS"
        bytes  = [Text.Encoding]::UTF8.GetByteCount($json)
        error  = ""
    }
}
catch {
    $checks += [pscustomobject]@{
        name   = "files"
        status = "FAIL"
        bytes  = 0
        error  = $_.Exception.Message
    }
}

try {
    $git = GetGit
    $json = $git | ConvertTo-Json -Depth 60 -Compress
    $checks += [pscustomobject]@{
        name   = "git"
        status = "PASS"
        bytes  = [Text.Encoding]::UTF8.GetByteCount($json)
        error  = ""
    }
}
catch {
    $checks += [pscustomobject]@{
        name   = "git"
        status = "FAIL"
        bytes  = 0
        error  = $_.Exception.Message
    }
}

$checks | Format-Table

$bad = @($checks | Where-Object { $_.status -ne "PASS" })
if ($bad.Count -gt 0) {
    exit 2
}

Write-Host "PASS core contract"
exit 0
