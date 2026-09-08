$ErrorActionPreference = "Stop"
$Here = $PSScriptRoot
$Repo = (Resolve-Path (Join-Path $Here "..\..")).Path
$Data = Join-Path $Here "data"
$Registry = Get-Content (Join-Path $Data "K01_FILE_REGISTRY_v2.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$Profiles = Get-Content (Join-Path $Data "K01_MACHINE_PROFILES_v2.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$ProfileName = $Profiles.active_profile
$Profile = $Profiles.profiles.$ProfileName
$Cad = $Profile.cad_root
$Port = 8765

function Resolve-EntryPath($e) {
    if ($e.kind -eq "repo") { return [IO.Path]::GetFullPath((Join-Path $Repo $e.path)) }
    if ($e.kind -eq "cad")  { return [IO.Path]::GetFullPath((Join-Path $Cad  $e.path)) }
    return $null
}
function JsonBytes($obj) {
    return [Text.Encoding]::UTF8.GetBytes(($obj | ConvertTo-Json -Depth 12))
}
function Send-Response($stream, $code, $contentType, [byte[]]$body) {
    $status = if ($code -eq 200) {"OK"} elseif ($code -eq 404) {"Not Found"} else {"Error"}
    $hdr = "HTTP/1.1 $code $status`r`nContent-Type: $contentType`r`nContent-Length: $($body.Length)`r`nConnection: close`r`n`r`n"
    $hb = [Text.Encoding]::ASCII.GetBytes($hdr)
    $stream.Write($hb,0,$hb.Length); $stream.Write($body,0,$body.Length); $stream.Flush()
}
function Git-Out([string[]]$args) {
    try { return (& git -C $Repo @args 2>&1 | Out-String).Trim() } catch { return "ERROR: $($_.Exception.Message)" }
}
function Get-GitState {
    $status = Git-Out @("status","--porcelain=v1")
    $lines = @()
    if ($status -and -not $status.StartsWith("ERROR:")) { $lines = $status -split "`r?`n" }
    [pscustomobject]@{
        branch = Git-Out @("branch","--show-current")
        last_commit = Git-Out @("log","-1","--format=%H|%cI|%s")
        origin = Git-Out @("remote","get-url","origin")
        dirty_count = $lines.Count
        untracked_count = @($lines | Where-Object { $_.StartsWith("??") }).Count
        status_lines = $lines
    }
}
function Get-QueryId($target) {
    if ($target -match '[?&]id=([^&]+)') { return [uri]::UnescapeDataString($matches[1]) }
    return ""
}
$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$Port)
$listener.Start()
Write-Host "================================================================================"
Write-Host "MARVILON K01 MEDTAS - Engineering Control Center v3"
Write-Host "================================================================================"
Write-Host "Repo: $Repo"
Write-Host "CAD : $Cad"
Write-Host "URL : http://127.0.0.1:$Port/"
Write-Host "No Python required. Close this window to stop the local server."
Start-Process "http://127.0.0.1:$Port/"

while ($true) {
    $client = $listener.AcceptTcpClient()
    try {
        $stream = $client.GetStream()
        $reader = New-Object IO.StreamReader($stream,[Text.Encoding]::ASCII,$false,8192,$true)
        $requestLine = $reader.ReadLine()
        while (($line=$reader.ReadLine()) -ne $null -and $line -ne "") {}
        if (-not $requestLine) { continue }
        $parts = $requestLine.Split(" ")
        $target = $parts[1]

        if ($target -eq "/" -or $target.StartsWith("/index")) {
            $p = Join-Path $Here "K01_Command_Center_v3.html"
            Send-Response $stream 200 "text/html; charset=utf-8" ([IO.File]::ReadAllBytes($p))
        }
        elseif ($target.StartsWith("/api/files")) {
            $rows = @()
            foreach ($e in $Registry.entries) {
                $p = Resolve-EntryPath $e
                $rows += [pscustomobject]@{
                    id=$e.id; name=$e.name; domain=$e.domain; kind=$e.kind; path=$e.path
                    resolved=$p; exists=(Test-Path $p)
                }
            }
            Send-Response $stream 200 "application/json; charset=utf-8" (JsonBytes ([pscustomobject]@{repo_root=$Repo;cad_root=$Cad;entries=$rows}))
        }
        elseif ($target.StartsWith("/api/git")) {
            Send-Response $stream 200 "application/json; charset=utf-8" (JsonBytes (Get-GitState))
        }
        elseif ($target.StartsWith("/api/open") -or $target.StartsWith("/api/reveal")) {
            $id = Get-QueryId $target
            $e = $Registry.entries | Where-Object { $_.id -eq $id } | Select-Object -First 1
            if (-not $e) { Send-Response $stream 404 "application/json" (JsonBytes @{error="unknown id"}); continue }
            $p = Resolve-EntryPath $e
            if (-not (Test-Path $p)) { Send-Response $stream 404 "application/json" (JsonBytes @{error="missing";path=$p}); continue }
            if ($target.StartsWith("/api/reveal")) {
                if (Test-Path $p -PathType Leaf) { Start-Process explorer.exe -ArgumentList "/select,`"$p`"" }
                else { Start-Process explorer.exe -ArgumentList "`"$p`"" }
            } else {
                Start-Process -FilePath $p
            }
            Send-Response $stream 200 "application/json" (JsonBytes @{ok=$true;path=$p})
        }
        else {
            Send-Response $stream 404 "text/plain; charset=utf-8" ([Text.Encoding]::UTF8.GetBytes("Not found"))
        }
    }
    catch {
        try { Send-Response $stream 500 "text/plain; charset=utf-8" ([Text.Encoding]::UTF8.GetBytes($_.Exception.Message)) } catch {}
    }
    finally { $client.Close() }
}
