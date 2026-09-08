param([string]$RepoRoot="",[string]$CadRoot="D:\Marvilon\K01\cad")
$ErrorActionPreference='Stop';if([string]::IsNullOrWhiteSpace($RepoRoot)){$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path}
$dir=Join-Path $CadRoot 'drawings\gate04d_c2r1_draft';$pdfs=@(Get-ChildItem $dir -Filter '*TPD_V3.PDF' -File -ErrorAction SilentlyContinue|Sort-Object Name)
if($pdfs.Count -lt 2){Write-Host 'Need P003 and P007 V3 PDFs first.' -ForegroundColor Red;pause;exit 2}
Write-Host 'Review each V3 PDF in SOLIDWORKS/PDF viewer for: no overlaps; correct section; readable tolerances/GD&T; title/material/projection; no spurious dimensions.'
$pdfs|ForEach-Object{Write-Host ('  '+$_.FullName)}
$ack=Read-Host 'Type APPROVE_V3_VISUAL only after reviewing all listed PDFs'
if($ack -ne 'APPROVE_V3_VISUAL'){Write-Host 'Not approved.';exit 3}
$rows=@();foreach($p in $pdfs){$rows+=[pscustomobject]@{path=$p.FullName;sha256=(Get-FileHash $p.FullName -Algorithm SHA256).Hash;modified=$p.LastWriteTime.ToString('s')}}
$r=[pscustomobject]@{schema='k01_drawing_visual_approval_v1';created=(Get-Date).ToString('o');status='PASS';scope='C2R1 TPD V3 PDFs';review_checks=@('no view/annotation overlap','section conveys internal geometry','release characteristics readable','title/material/projection readable','no spurious AutoDimension dump','no conflicting/duplicate controlled dimensions');files=$rows;approval='explicit local engineering approval'}
$out=Join-Path $RepoRoot 'reports\drawings\K01_DRAWING_VISUAL_APPROVAL_CURRENT.json';New-Item ([IO.Path]::GetDirectoryName($out)) -ItemType Directory -Force|Out-Null;$r|ConvertTo-Json -Depth 10|Set-Content $out -Encoding UTF8;Write-Host "Visual approval recorded: $out"
