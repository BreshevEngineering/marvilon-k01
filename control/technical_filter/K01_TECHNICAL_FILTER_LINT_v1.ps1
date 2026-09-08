param([string]$RepoRoot="")
$ErrorActionPreference='Stop';if([string]::IsNullOrWhiteSpace($RepoRoot)){$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path}
$schema=Get-Content (Join-Path $PSScriptRoot 'K01_TECHNICAL_FILTER_SCHEMA_v1.json') -Raw -Encoding UTF8|ConvertFrom-Json
$f=Get-Content (Join-Path $PSScriptRoot 'K01_J2_C2R1_TECHNICAL_FILTER_v1.json') -Raw -Encoding UTF8|ConvertFrom-Json
$err=@();$required=@($schema.gates);$present=@($f.gates.gate);foreach($g in $required){if($present -notcontains $g){$err+="missing gate: $g"}}
foreach($g in @($f.gates)){foreach($k in @($schema.gate_required_fields)){if(-not($g.PSObject.Properties.Name -contains $k)){$err+="$($g.gate): missing field $k"}};if(@($g.source_ids).Count -eq 0){$err+="$($g.gate): no source_ids"};if([string]::IsNullOrWhiteSpace([string]$g.verification_method)){$err+="$($g.gate): no verification_method"}}
$r=[pscustomobject]@{schema='k01_technical_filter_lint_v1';created=(Get-Date).ToString('o');status=if($err.Count){'HOLD'}else{'PASS'};expected_gates=$required.Count;present_gates=$present.Count;errors=$err}
$out=Join-Path $RepoRoot 'reports\control\K01_TECHNICAL_FILTER_LINT_CURRENT.json';New-Item ([IO.Path]::GetDirectoryName($out)) -ItemType Directory -Force|Out-Null;$r|ConvertTo-Json -Depth 10|Set-Content $out -Encoding UTF8;Write-Host "Technical filter lint: $($r.status) gates=$($present.Count)/$($required.Count) errors=$($err.Count)";if($err.Count){$err|ForEach-Object{Write-Host $_ -ForegroundColor Red};exit 2}
