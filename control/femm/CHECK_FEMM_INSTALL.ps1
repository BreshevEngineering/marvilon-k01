param([string]$RepoRoot = "")

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$candidates = @(
    "C:\femm42\bin\femm.exe",
    "C:\Program Files\femm42\bin\femm.exe",
    "C:\Program Files\FEMM 4.2\bin\femm.exe",
    "C:\Program Files (x86)\femm42\bin\femm.exe"
)

$exe = ""

foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
        $exe = $candidate
        break
    }
}

if ([string]::IsNullOrWhiteSpace($exe)) {
    try {
        $cmd = Get-Command femm.exe -ErrorAction Stop
        $exe = $cmd.Source
    }
    catch {
        $exe = ""
    }
}

$status = "HOLD_FEMM_NOT_FOUND"
$sha256 = ""
$fileVersion = ""

if (-not [string]::IsNullOrWhiteSpace($exe)) {
    $status = "PASS_FEMM_FOUND"
    $sha256 = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
    try {
        $fileVersion = (Get-Item -LiteralPath $exe).VersionInfo.FileVersion
    }
    catch {
        $fileVersion = ""
    }
}

$out = Join-Path $RepoRoot "reports\femm\FEMM_INSTALL_CURRENT.json"
New-Item ([IO.Path]::GetDirectoryName($out)) -ItemType Directory -Force | Out-Null

[pscustomobject]@{
    schema               = "k01.femm_solver_install.v1"
    created              = (Get-Date).ToString("o")
    status               = $status
    executable           = $exe
    executable_sha256    = $sha256
    file_version         = $fileVersion
    automation_baseline  = "NATIVE_LUA_COMMAND_LINE"
    command_template     = "femm.exe -lua-script=<script.lua> -windowhide"
    pyfemm_required      = $false
    release_rule         = "Every FEMM evidence record must include this executable SHA-256, the model/input hashes, and the automation-script hash."
} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $out -Encoding UTF8

Write-Host "FEMM: $status"
Write-Host "Executable: $exe"
Write-Host "SHA256: $sha256"
Write-Host "Version: $fileVersion"
Write-Host "Report: $out"

if ($status -ne "PASS_FEMM_FOUND") {
    exit 2
}

exit 0
