param(
  [string]$RepoRoot="",
  [string]$CadRoot="D:\Marvilon\K01\cad"
)
$ErrorActionPreference='Stop'
if([string]::IsNullOrWhiteSpace($RepoRoot)){$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path}
$out=Join-Path $RepoRoot 'reports\control\K01_MEDTAS_V8_PREFLIGHT_CURRENT.json'
New-Item ([IO.Path]::GetDirectoryName($out)) -ItemType Directory -Force|Out-Null

$checks=@()
function Add-Check($id,$kind,$path,$required=$true){
  $exists=Test-Path -LiteralPath $path
  $checks+=[pscustomobject]@{id=$id;kind=$kind;required=$required;exists=$exists;path=$path}
}
function Add-Json($id,$path,$required=$true){
  $ok=$false;$err=''
  if(Test-Path -LiteralPath $path){
    try{Get-Content $path -Raw -Encoding UTF8|ConvertFrom-Json|Out-Null;$ok=$true}catch{$err=$_.Exception.Message}
  }
  $checks+=[pscustomobject]@{id=$id;kind='JSON';required=$required;exists=(Test-Path -LiteralPath $path);valid=$ok;path=$path;error=$err}
}


function Add-RegistrySemantic($id,$path,$required=$true){
  $exists=Test-Path -LiteralPath $path -PathType Leaf;$ok=$false;$err=''
  if($exists){
    try{
      $j=Get-Content $path -Raw -Encoding UTF8|ConvertFrom-Json
      $ids=@{};$issues=@()
      foreach($e in @($j.entries)){
        foreach($k in @('id','name','domain','root')){
          if(-not($e.PSObject.Properties.Name -contains $k) -or [string]::IsNullOrWhiteSpace([string]$e.$k)){$issues+="entry missing $k"}
        }
        if($e.root -notin @('repo','cad')){$issues+="invalid root for $($e.id): $($e.root)"}
        if($ids.ContainsKey([string]$e.id)){$issues+="duplicate id: $($e.id)"}else{$ids[[string]$e.id]=$true}
        $hasCandidates=($e.PSObject.Properties.Name -contains 'candidates' -and @($e.candidates).Count -gt 0)
        $hasPatterns=($e.PSObject.Properties.Name -contains 'patterns' -and @($e.patterns).Count -gt 0)
        if(-not($hasCandidates -or $hasPatterns)){$issues+="entry has neither candidates nor patterns: $($e.id)"}
      }
      $ok=($issues.Count -eq 0);if(-not $ok){$err=$issues -join ' | '}
    }catch{$err=$_.Exception.Message}
  }
  $checks+=[pscustomobject]@{id=$id;kind='REGISTRY_SEMANTIC';required=$required;exists=$exists;valid=$ok;path=$path;error=$err}
}


function Add-EnglishUi($id,$path,$required=$true){
  $exists=Test-Path -LiteralPath $path -PathType Leaf;$ok=$false;$err=''
  if($exists){
    try{
      $text=Get-Content -LiteralPath $path -Raw -Encoding UTF8
      $m=[regex]::Matches($text,'[А-Яа-яЁё]')
      $ok=($m.Count -eq 0)
      if(-not $ok){$err="Cyrillic UI text found: count=$($m.Count)"}
    }catch{$err=$_.Exception.Message}
  }
  $checks+=[pscustomobject]@{id=$id;kind='UI_LANGUAGE';required=$required;exists=$exists;valid=$ok;path=$path;error=$err}
}

function Add-PowerShellSyntax($id,$path,$required=$true){
  $exists=Test-Path -LiteralPath $path -PathType Leaf
  $ok=$false;$err=''
  if($exists){
    try{
      $tokens=$null;$errors=$null
      [System.Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)|Out-Null
      $ok=(@($errors).Count -eq 0)
      if(-not $ok){$err=(@($errors)|ForEach-Object{$_.Message}) -join ' | '}
    }catch{$err=$_.Exception.Message}
  }
  $checks+=[pscustomobject]@{id=$id;kind='POWERSHELL_SYNTAX';required=$required;exists=$exists;valid=$ok;path=$path;error=$err}
}

Add-Check 'POWERSHELL' 'runtime' "$PSHOME\powershell.exe"
Add-Check 'GIT' 'runtime' ((Get-Command git.exe -ErrorAction SilentlyContinue).Source) $false
Add-Check 'SW_INTEROP_SLDWORKS' 'interop' "$env:ProgramFiles\SOLIDWORKS Corp\SOLIDWORKS\api\redist\SolidWorks.Interop.sldworks.dll"
Add-Check 'SW_INTEROP_SWCONST' 'interop' "$env:ProgramFiles\SOLIDWORKS Corp\SOLIDWORKS\api\redist\SolidWorks.Interop.swconst.dll"
Add-Check 'CSC64' 'compiler' "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"

foreach($r in @(
 'control\command_center\K01_Command_Center_v8.html',
 'control\command_center\cc_server_v8.ps1',
 'control\command_center\cc_api_core_v8.ps1',
 'control\command_center\RUN_K01_COMMAND_CENTER_SELFTEST.ps1',
 'control\command_center\RUN_K01_COMMAND_CENTER_SELFTEST.cmd',
 'control\system\K01_MEDTAS_RELIABILITY_STANDARD_v1.json',
 'control\command_center\data\K01_FILE_REGISTRY_v8.json',
 'control\system\K01_MEDTAS_RELIABILITY_STANDARD_v1.json',
 'control\state\K01_STATE_ENGINE_v8.ps1',
 'control\release\K01_J2_C2R1_PRODUCTION_RELEASE_PACKAGE_v1.json',
 'control\technical_filter\K01_J2_C2R1_TECHNICAL_FILTER_v1.json',
 'control\drawings\K01_DRAWING_INTENT_LINT_v2.ps1',
 'control\drawings\K01_DRAWING_VISUAL_APPROVAL_v1.ps1',
 'cad_api\gates\gate04d_c2r1\00_GATE04D_C2R1_ALL.cmd',
 'cad_api\gates\gate04d_c2r1\06_GATE04D_C2R1_DRAWINGS_V3.cmd',
 'cad_api\gates\gate04e_p006_service\RUN_GATE04E_P006_SERVICE_BUILD.cmd',
 'cad_api\gates\gate04e_p006_service\K01Gate04E_P006_ServiceDrive.cs',
 'cad_api\gates\gate04e_p006_service\K01Gate04E_P006_ServiceVerify.cs',
 'cad_api\bom\03_BOM_PROPERTY_PROJECTION_DRY_RUN.cmd',
 'cad_api\bom\04_BOM_PROPERTY_PROJECTION_APPLY.cmd',
 'cad_api\bom\RUN_K01_BOM_PIPELINE_C2R1.cmd',
 'control\git\RUN_K01_GIT_CLASSIFY_V2.cmd',
 'control\system\K01_PART_IDENTITY_AUTHORITY_v1.json',
 'control\digital_thread\K01_MEDTAS_DIGITAL_THREAD_ARCHITECTURE_v2.json',
 'control\assembly\K01_A001_ASSEMBLY_MATURITY_v1.json',
 'control\femm\K01_FEMM_SETUP_v1.json',
 'control\femm\K01_FEMM_SCREENING_PLAN_v1.json',
 'control\femm\CHECK_K01_FEMM_INSTALL.cmd',
 'control\git\CHECK_K01_GITHUB_REMOTE.cmd',
 'control\visualization\K01_VISUAL_CONTEXT_POLICY_v1.json',
 'cad_api\bridge\K01SolidWorksLiveBridge.cs',
 'cad_api\bridge\START_K01_SOLIDWORKS_LIVE_BRIDGE.cmd'
)){Add-Check ("REPO:"+$r) 'repo_file' (Join-Path $RepoRoot $r)}

foreach($r in @(
 'control\command_center\data\K01_FILE_REGISTRY_v8.json',
 'control\release\K01_J2_C2R1_PRODUCTION_RELEASE_PACKAGE_v1.json',
 'control\technical_filter\K01_J2_C2R1_TECHNICAL_FILTER_v1.json',
 'control\drawings\K01_TPD_DRAWING_ASSURANCE_STANDARD_v1.json',
 'control\drawings\spec\K01-D-003_P003_DRAWING_INTENT_v1.json',
 'control\drawings\spec\K01-D-005_P006_DRAWING_INTENT_v1.json',
 'control\drawings\spec\K01-D-006_P007_DRAWING_INTENT_v1.json',
 'control\workpacks\K01_T03_PILOT_TOOL_WORKPACKAGE_v2.json',
 'control\workpacks\K01_T04_MEDIA_ENVELOPE_v1.json',
 'control\workpacks\K01_T04_SEAL_PRELOAD_WORKPACKAGE_v1.json',
 'control\workpacks\K01_T05_J2_CLAMP_STRENGTH_WORKPACKAGE_v1.json',
 'control\workpacks\K01_T06_THERMAL_GALLING_SERVICE_WORKPACKAGE_v1.json',
 'control\workpacks\K01_T07_P007_STRUCTURAL_REFRESH_v1.json',
 'control\workpacks\K01_T08_BOM_PROPERTY_PROJECTION_v1.json',
 'control\workpacks\K01_T09_DRAWING_TPD_RELEASE_v1.json',
 'control\workpacks\K01_T10_FEMM_BENCH_RELEASE_v1.json',
 'control\evidence\K01_SOURCE_REGISTRY_v2.json',
 'control\digital_thread\K01_MEDTAS_DIGITAL_THREAD_ARCHITECTURE_v2.json',
 'control\assembly\K01_A001_ASSEMBLY_MATURITY_v1.json',
 'control\femm\K01_FEMM_SETUP_v1.json',
 'control\femm\K01_FEMM_SCREENING_PLAN_v1.json',
 'control\visualization\K01_VISUAL_CONTEXT_POLICY_v1.json'
)){Add-Json ("JSON:"+$r) (Join-Path $RepoRoot $r)}

Add-EnglishUi 'UI_LANGUAGE_ENGLISH' (Join-Path $RepoRoot 'control\command_center\K01_Command_Center_v8.html')

Add-RegistrySemantic 'REGISTRY_SEMANTIC_V8' (Join-Path $RepoRoot 'control\command_center\data\K01_FILE_REGISTRY_v8.json')

Add-PowerShellSyntax 'PS_SYNTAX_STATE_ENGINE' (Join-Path $RepoRoot 'control\state\K01_STATE_ENGINE_v8.ps1')
Add-PowerShellSyntax 'PS_SYNTAX_CENTER_SERVER' (Join-Path $RepoRoot 'control\command_center\cc_server_v8.ps1')
Add-PowerShellSyntax 'PS_SYNTAX_CENTER_CORE' (Join-Path $RepoRoot 'control\command_center\cc_api_core_v8.ps1')
Add-PowerShellSyntax 'PS_SYNTAX_CENTER_SELFTEST' (Join-Path $RepoRoot 'control\command_center\RUN_K01_COMMAND_CENTER_SELFTEST.ps1')
Add-PowerShellSyntax 'PS_SYNTAX_PREFLIGHT' $MyInvocation.MyCommand.Path

Add-Check 'CAD_PRODUCTION_A001' 'cad' (Join-Path $CadRoot 'assemblies\K01-A-001_Calibration_Module.SLDASM') $false
Add-Check 'CAD_STABLE_P003' 'cad' (Join-Path $CadRoot 'parts\K01-P-003_Cartridge_Body.SLDPRT') $false
Add-Check 'CAD_STABLE_P006' 'cad' (Join-Path $CadRoot 'parts\K01-P-006_Retaining_Plug.SLDPRT') $false
Add-Check 'CAD_STABLE_P007' 'cad' (Join-Path $CadRoot 'parts\K01-P-007_Hermetic_Magnetic_Can.SLDPRT') $false

$hard=@($checks|Where-Object{$_.required -and (-not $_.exists -or (($_.kind -eq 'JSON' -or $_.kind -eq 'POWERSHELL_SYNTAX' -or $_.kind -eq 'REGISTRY_SEMANTIC' -or $_.kind -eq 'UI_LANGUAGE') -and -not $_.valid))})
$status=if($hard.Count -eq 0){'PASS_INFRASTRUCTURE'}else{'HOLD_MISSING_REQUIRED'}
$r=[pscustomobject]@{
 schema='k01_medtas_v8_4_preflight'
 created=(Get-Date).ToString('o')
 status=$status
 repo_root=$RepoRoot
 cad_root=$CadRoot
 required_failures=$hard.Count
 checks=$checks
 note='This preflight is read-only. It does not modify CAD, Git index, BOM metadata or release status.'
}
$r|ConvertTo-Json -Depth 20|Set-Content $out -Encoding UTF8
Write-Host "MEDTAS v8.4 preflight: $status | required failures=$($hard.Count)"
Write-Host "Report: $out"
$hard|ForEach-Object{Write-Host ("HOLD: "+$_.id+" -> "+$_.path) -ForegroundColor Red}
if($hard.Count){exit 2}
exit 0
