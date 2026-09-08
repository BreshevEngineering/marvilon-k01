param([string]$RepoRoot="")
$ErrorActionPreference="Stop"
if([string]::IsNullOrWhiteSpace($RepoRoot)){$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path}
$inp=Get-Content (Join-Path $RepoRoot "control\calculations\K01_T05_CLAMP_SCREEN_INPUT.json") -Raw -Encoding UTF8|ConvertFrom-Json
$g=$inp.geometry;$p=$inp.pressure;$f=$inp.fastener;$s=$inp.seal_screen
$outer=([double]$g.flange_OD_mm-[double]$g.PCD_mm-[double]$g.clearance_hole_D_mm)/2.0
$inner=([double]$g.PCD_mm-[double]$g.clearance_hole_D_mm-[double]$g.gland_worst_OD_mm)/2.0
$area=[math]::PI*[math]::Pow(([double]$g.seal_meanline_D_mm/2.0),2)
$pressureN=([double]$p.qualification_abs_bar*100000.0)*($area*1e-6)
$totalClamp=[double]$g.screw_count*[double]$f.candidate_preload_N_per_screw
$residual=$totalClamp-[double]$s.compression_force_upper_bound_N-$pressureN
$threadSF=[double]$f.prior_thread_strip_screen_N_per_screw/[double]$f.candidate_preload_N_per_screw
$localSF=[double]$f.P007_316L_screen_yield_MPa/[double]$f.prior_local_bending_screen_MPa_at_300N
$status=if($outer -ge 1.8 -and $inner -ge 1.5 -and $residual -gt 0 -and $threadSF -ge 3.0 -and $localSF -ge 1.2){"SCREEN_PASS_LOCAL_FEA_AND_TORQUE_PROCESS_OPEN"}else{"HOLD"}
$r=[pscustomobject]@{
 schema="k01_t05_clamp_screen_result_v1";created=(Get-Date).ToString("o");status=$status;
 outer_ligament_mm=$outer;inner_ligament_mm=$inner;pressure_separating_force_N=$pressureN;
 total_candidate_clamp_N=$totalClamp;seal_force_screen_upper_bound_N=[double]$s.compression_force_upper_bound_N;
 residual_clamp_screen_N=$residual;thread_strip_SF=$threadSF;local_bending_screen_SF=$localSF;
 release_holds=@("Exact FKM compound compression-force confirmation","M2.5 screw grade/finish/anti-galling strategy","torque-preload process","local flange/contact FEA or equivalent confirmation")
}
$out=Join-Path $RepoRoot "reports\calculations\K01_T05_CLAMP_SCREEN_CURRENT.json"
New-Item ([IO.Path]::GetDirectoryName($out)) -ItemType Directory -Force|Out-Null
$r|ConvertTo-Json -Depth 20|Set-Content -LiteralPath $out -Encoding UTF8
$r|Format-List
Write-Host "Report: $out"
if($status -eq "HOLD"){exit 2}else{exit 0}
