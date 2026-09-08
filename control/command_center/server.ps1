param([int]$Port=8765)
$ErrorActionPreference='Stop'
$Here=$PSScriptRoot
. (Join-Path $Here 'core.ps1')

function B($o){[Text.Encoding]::UTF8.GetBytes(($o|ConvertTo-Json -Depth 60 -Compress))}
function TB([string]$s){[Text.Encoding]::UTF8.GetBytes($s)}
function Reason([int]$c){switch($c){200{'OK'};404{'Not Found'};405{'Method Not Allowed'};500{'Internal Server Error'};default{'Response'}}}
function Send($s,[int]$c,[string]$t,[byte[]]$body){$h="HTTP/1.1 $c $(Reason $c)`r`nContent-Type: $t`r`nCache-Control: no-store`r`nContent-Length: $($body.Length)`r`nConnection: close`r`n`r`n";$hb=[Text.Encoding]::ASCII.GetBytes($h);$s.Write($hb,0,$hb.Length);$s.Write($body,0,$body.Length);$s.Flush()}
function QueryId([string]$target){if($target -match '[?&]id=([^&]+)'){return [Uri]::UnescapeDataString($matches[1])};return ''}

$actions=@{
 'RUN_P006_SERVICE'=Repo 'cad_api\gates\gate04e_p006_service\RUN_GATE04E_P006_SERVICE_BUILD.cmd'
 'REPORT_REQUIREMENTS'=Repo 'control\requirements\REPORT_REQUIREMENTS_COVERAGE.cmd'
 'CHECK_FEMM_INSTALL'=Repo 'control\femm\CHECK_K01_FEMM_INSTALL.cmd'
 'BACKFILL_PROVENANCE'=Repo 'control\provenance\BACKFILL_C2R1_PROVENANCE.cmd'
 'REFRESH_BOM'=Repo 'control\bom\REFRESH_BOM_READ_ONLY.cmd'
 'NORMALIZE_BOM'=Repo 'control\bom\NORMALIZE_BOM.cmd'
 'BUILD_AI_HANDOFF'=Repo 'control\handoff\BUILD_AI_HANDOFF.cmd'
 'START_SW_BRIDGE'=Repo 'cad_api\bridge\START_K01_SOLIDWORKS_LIVE_BRIDGE.cmd'
 'CHECK_GITHUB_REMOTE'=Repo 'control\git\CHECK_K01_GITHUB_REMOTE.cmd'
 'RUN_GIT_CLASSIFIER'=Repo 'control\git\RUN_K01_GIT_CLASSIFY.cmd'
 'OPEN_TPD_ARCH'=Repo 'control\drawings\tpd_automation_architecture.json'
}

$listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$Port);$listener.Start()
Write-Host "MEDTAS K01 stable core";Write-Host "http://127.0.0.1:$Port/"
Start-Process "http://127.0.0.1:$Port/"

while($true){
 $client=$listener.AcceptTcpClient();$stream=$null;$target='';$method=''
 try{
  $stream=$client.GetStream();$reader=New-Object IO.StreamReader($stream,[Text.Encoding]::ASCII,$false,8192,$true)
  $line=$reader.ReadLine();if([string]::IsNullOrWhiteSpace($line)){continue}
  $parts=$line.Split(' ');$method=$parts[0].ToUpperInvariant();$target=$parts[1]
  while(($h=$reader.ReadLine()) -ne $null -and $h -ne ''){}

  if($method -eq 'GET' -and ($target -eq '/' -or $target.StartsWith('/index'))){Send $stream 200 'text/html; charset=utf-8' ([IO.File]::ReadAllBytes((Join-Path $Here 'index.html')));continue}
  if($method -eq 'GET' -and $target -eq '/styles.css'){Send $stream 200 'text/css; charset=utf-8' ([IO.File]::ReadAllBytes((Join-Path $Here 'styles.css')));continue}
  if($method -eq 'GET' -and $target -eq '/app.js'){Send $stream 200 'application/javascript; charset=utf-8' ([IO.File]::ReadAllBytes((Join-Path $Here 'app.js')));continue}

  if($method -eq 'GET' -and $target.StartsWith('/api/state')){Send $stream 200 'application/json; charset=utf-8' (B ([pscustomobject]@{ok=$true;state=(GetState)}));continue}
  if($method -eq 'GET' -and $target.StartsWith('/api/files')){Send $stream 200 'application/json; charset=utf-8' (B ([pscustomobject]@{ok=$true;files=(GetFiles)}));continue}
  if($method -eq 'GET' -and $target.StartsWith('/api/git')){Send $stream 200 'application/json; charset=utf-8' (B ([pscustomobject]@{ok=$true;git=(GetGit)}));continue}
  if($method -eq 'GET' -and $target.StartsWith('/api/bom')){Send $stream 200 'application/json; charset=utf-8' (B ([pscustomobject]@{ok=$true;bom=(GetBom)}));continue}
  if($method -eq 'GET' -and $target.StartsWith('/api/solidworks')){Send $stream 200 'application/json; charset=utf-8' (B ([pscustomobject]@{ok=$true;solidworks=(GetSolidWorksLive)}));continue}

  if($target.StartsWith('/api/action') -and $method -ne 'POST'){Send $stream 405 'application/json; charset=utf-8' (B ([pscustomobject]@{ok=$false;error='Actions require POST'}));continue}
  if($method -eq 'POST' -and $target.StartsWith('/api/action')){
    $id=QueryId $target
    if($id.StartsWith('OPEN_FILE:')){
      $fid=$id.Substring(10);$e=$script:Registry.entries|Where-Object{$_.id -eq $fid}|Select-Object -First 1
      if($null -eq $e){Send $stream 404 'application/json; charset=utf-8' (B ([pscustomobject]@{ok=$false;error='unknown file id'}));continue}
      $p=ResolveEntry $e
      if(-not(Test-Path -LiteralPath $p -PathType Leaf)){Send $stream 404 'application/json; charset=utf-8' (B ([pscustomobject]@{ok=$false;error='file missing';path=$p}));continue}
      Start-Process -FilePath $p;Send $stream 200 'application/json; charset=utf-8' (B ([pscustomobject]@{ok=$true;path=$p}));continue
    }
    if(-not $actions.ContainsKey($id)){Send $stream 404 'application/json; charset=utf-8' (B ([pscustomobject]@{ok=$false;error='unknown action';id=$id}));continue}
    $p=[string]$actions[$id]
    if(-not(Test-Path -LiteralPath $p -PathType Leaf)){Send $stream 404 'application/json; charset=utf-8' (B ([pscustomobject]@{ok=$false;error='action target missing';path=$p}));continue}
    if($p.ToLowerInvariant().EndsWith('.cmd')){Start-Process -FilePath 'cmd.exe' -ArgumentList '/k',("`"$p`"") -WorkingDirectory ([IO.Path]::GetDirectoryName($p))}
    else{Start-Process -FilePath $p}
    Send $stream 200 'application/json; charset=utf-8' (B ([pscustomobject]@{ok=$true;id=$id;path=$p}));continue
  }

  Send $stream 404 'text/plain; charset=utf-8' (TB 'not found')
 }catch{
  if($null -ne $stream){try{Send $stream 500 'application/json; charset=utf-8' (B ([pscustomobject]@{ok=$false;endpoint=$target;error=$_.Exception.Message}))}catch{}}
 }finally{$client.Close()}
}
