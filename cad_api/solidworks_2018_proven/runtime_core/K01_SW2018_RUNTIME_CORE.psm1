Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-K01Sw2018Interop {
    param([Parameter(Mandatory=$true)][string]$FileName)
    $candidates = @(
        "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist\$FileName",
        "C:\Program Files (x86)\SOLIDWORKS Corp\SOLIDWORKS\api\redist\$FileName"
    )
    foreach ($p in $candidates) {
        if (Test-Path -LiteralPath $p) { return $p }
    }
    throw "SW2018 interop not found: $FileName"
}

function Get-K01Csc {
    $candidates = @(
        "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
        "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path -LiteralPath $p) { return $p }
    }
    throw "C# compiler not found."
}

function Build-K01Sw2018Helper {
    param(
        [Parameter(Mandatory=$true)][string[]]$Sources,
        [Parameter(Mandatory=$true)][string]$BuildDir,
        [Parameter(Mandatory=$true)][string]$ExeName
    )

    New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
    $sld = Get-K01Sw2018Interop "SolidWorks.Interop.sldworks.dll"
    $con = Get-K01Sw2018Interop "SolidWorks.Interop.swconst.dll"
    $csc = Get-K01Csc
    $exe = Join-Path $BuildDir $ExeName

    Remove-Item -LiteralPath $exe -Force -ErrorAction SilentlyContinue

    $args = @("/nologo","/langversion:5","/target:exe","/platform:x64","/optimize+",
              "/r:$sld","/r:$con","/r:System.Web.Extensions.dll","/out:$exe") + $Sources

    # IMPORTANT: native stdout inside a PowerShell function is pipeline output.
    # Capture it and re-emit via Write-Host so Build-K01Sw2018Helper returns ONLY $exe.
    $compileOutput = @(& $csc @args)
    $compileRc = $LASTEXITCODE
    foreach ($line in $compileOutput) { Write-Host $line }
    if ($compileRc -ne 0) { throw "COMPILE_FAILED" }

    Copy-Item -LiteralPath $sld -Destination (Join-Path $BuildDir "SolidWorks.Interop.sldworks.dll") -Force
    Copy-Item -LiteralPath $con -Destination (Join-Path $BuildDir "SolidWorks.Interop.swconst.dll") -Force

    Push-Location $BuildDir
    try {
        # Same rule for the runtime probe: show diagnostics, do not leak them into return value.
        $probeOutput = @(& $exe "--runtime-probe")
        $probeRc = $LASTEXITCODE
        foreach ($line in $probeOutput) { Write-Host $line }
        if ($probeRc -ne 0) { throw "RUNTIME_BIND_PROBE_FAILED" }
    } finally { Pop-Location }

    return $exe
}

Export-ModuleMember -Function Get-K01Sw2018Interop,Get-K01Csc,Build-K01Sw2018Helper
