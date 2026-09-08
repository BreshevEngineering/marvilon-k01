param([string]$RepoRoot="",[string]$CadRoot="D:\Marvilon\K01\cad")
$ErrorActionPreference='Stop'
if([string]::IsNullOrWhiteSpace($RepoRoot)){$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path}
$register=Join-Path $PSScriptRoot 'REGISTER_EVIDENCE.ps1'

$records=@(
  @{
    evidence='reports\cad\current\K01_GATE04D_C2R1_TYPED_BUILD.json'
    id='EV-C2R1-BUILD'
    script='cad_api\gates\gate04d_c2r1\K01Gate04D_C2R1_Build.cs'
    inputs=@(
      "$CadRoot\candidates\gate04d_c2r1\K01-P-003_Cartridge_Body_GATE04D_C2R1_CANDIDATE.SLDPRT",
      "$CadRoot\candidates\gate04d_c2r1\K01-P-007_Hermetic_Magnetic_Can_GATE04D_C2R1_CANDIDATE.SLDPRT",
      'cad_api\gates\gate04d_c2r1\K01_GATE04D_C2R1_PARAMS_v1.json'
    )
  },
  @{
    evidence='reports\cad\current\K01_GATE04D_C2R1_VERIFY.json'
    id='EV-C2R1-VERIFY'
    script='cad_api\gates\gate04d_c2r1\K01Gate04D_C2R1_Verify.cs'
    inputs=@(
      "$CadRoot\candidates\gate04d_c2r1\verification\K01-A-001_GATE04D_C2R1_VERIFY.SLDASM",
      "$CadRoot\candidates\gate04d_c2r1\K01-P-003_Cartridge_Body_GATE04D_C2R1_CANDIDATE.SLDPRT",
      "$CadRoot\candidates\gate04d_c2r1\K01-P-007_Hermetic_Magnetic_Can_GATE04D_C2R1_CANDIDATE.SLDPRT",
      'cad_api\gates\gate04d_c2r1\K01_GATE04D_C2R1_PARAMS_v1.json'
    )
  },
  @{
    evidence='reports\cad\current\K01_GATE04D_C2R1_INTERFERENCE.json'
    id='EV-C2R1-INTERFERENCE'
    script='cad_api\gates\gate04d_c2r1\K01Gate04D_C2R1_Verify.cs'
    inputs=@(
      "$CadRoot\candidates\gate04d_c2r1\verification\K01-A-001_GATE04D_C2R1_VERIFY.SLDASM"
    )
  }
)

foreach($r in $records){
  $ev=Join-Path $RepoRoot $r.evidence
  $sc=Join-Path $RepoRoot $r.script
  $missing=@()
  foreach($x in @($r.inputs)){
    $p=if([IO.Path]::IsPathRooted([string]$x)){[string]$x}else{Join-Path $RepoRoot ([string]$x)}
    if(-not(Test-Path -LiteralPath $p -PathType Leaf)){$missing+=$p}
  }
  if(-not(Test-Path -LiteralPath $ev -PathType Leaf)){$missing+=$ev}
  if(-not(Test-Path -LiteralPath $sc -PathType Leaf)){$missing+=$sc}
  if($missing.Count){
    Write-Host "HOLD $($r.id): missing inputs" -ForegroundColor Yellow
    $missing|ForEach-Object{Write-Host "  $_"}
    continue
  }
  & $register -EvidencePath $ev -EvidenceId $r.id -InputPaths @($r.inputs) -ToolName 'SOLIDWORKS 2018 API' -ToolVersion '26.0.1' -ScriptPath $sc -RepoRoot $RepoRoot
}
