param([string]$RepoRoot="")
$ErrorActionPreference='Stop'
if([string]::IsNullOrWhiteSpace($RepoRoot)){$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path}
$out=Join-Path $RepoRoot 'reports\femm\K01_FEMM_INSTALL_CURRENT.json'
New-Item ([IO.Path]::GetDirectoryName($out)) -ItemType Directory -Force|Out-Null

$candidates=@(
 'C:\femm42\bin\femm.exe',
 'C:\Program Files\femm42\bin\femm.exe',
 'C:\Program Files\FEMM 4.2\bin\femm.exe',
 'C:\Program Files (x86)\femm42\bin\femm.exe'
)
$found=''
foreach($p in $candidates){if(Test-Path -LiteralPath $p -PathType Leaf){$found=$p;break}}
if([string]::IsNullOrWhiteSpace($found)){
  try{$cmd=Get-Command femm.exe -ErrorAction Stop;$found=$cmd.Source}catch{}
}

$py=''
try{$pycmd=Get-Command py.exe -ErrorAction Stop;$py=$pycmd.Source}catch{}
$python=''
try{$pcmd=Get-Command python.exe -ErrorAction Stop;$python=$pcmd.Source}catch{}

$status=if($found){'PASS_FEMM_FOUND'}else{'HOLD_FEMM_NOT_INSTALLED'}
$r=[pscustomobject]@{
 schema='k01_femm_install_v1'
 created=(Get-Date).ToString('o')
 status=$status
 femm_exe=$found
 baseline_expected='FEMM 4.2 64-bit Stable Distribution 21Apr2019'
 automation_baseline='NATIVE_LUA_COMMAND_LINE'
 command_template='femm.exe -lua-script=<script.lua> -windowhide'
 py_launcher=$py
 python_exe=$python
 pyfemm_required=$false
 official_download='https://www.femm.info/doku/doku.php?id=Download'
 note='No FEMM installation or Python package is modified by this check.'
}
$r|ConvertTo-Json -Depth 10|Set-Content $out -Encoding UTF8
Write-Host "FEMM: $status"
if($found){Write-Host "Executable: $found";Write-Host "Automation baseline: native Lua command line"}
else{Write-Host "Install FEMM 4.2 64-bit stable distribution from the official FEMM download page." -ForegroundColor Yellow}
Write-Host "Report: $out"
if($found){exit 0}else{exit 2}
