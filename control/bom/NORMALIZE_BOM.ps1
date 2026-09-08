param([string]$RepoRoot = "")

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$candidates = @(
    (Join-Path $RepoRoot "bom\K01_BOM_study_c2r1.json"),
    (Join-Path $RepoRoot "reports\bom\K01_BOM_study_c2r1.json"),
    (Join-Path $RepoRoot "reports\bom\K01_BOM_RECONCILIATION_study_c2r1.json")
)

$source = ""
foreach ($p in $candidates) {
    if (Test-Path -LiteralPath $p -PathType Leaf) {
        $source = $p
        break
    }
}

if ([string]::IsNullOrWhiteSpace($source)) {
    throw "No current C2R1 BOM JSON was found."
}

$j = Get-Content -LiteralPath $source -Raw -Encoding UTF8 | ConvertFrom-Json
$rows = @()

foreach ($r in @($j.rows)) {
    $path = [string]$r.path
    $raw = [string]$r.observed_part_no
    if ([string]::IsNullOrWhiteSpace($raw) -and ($r.PSObject.Properties.Name -contains "PartNo")) {
        $raw = [string]$r.PartNo
    }

    $identityText = $path + " " + $raw
    $m = [regex]::Match($identityText, 'K01-[PB]-\d{3}')
    $canonical = if ($m.Success) { $m.Value } else { $raw }

    $description = [string]$r.description
    if ([string]::IsNullOrWhiteSpace($description) -and ($r.PSObject.Properties.Name -contains "Description")) {
        $description = [string]$r.Description
    }

    if ([string]::IsNullOrWhiteSpace($description)) {
        $fileStem = [IO.Path]::GetFileNameWithoutExtension($path)
        $fileStem = $fileStem -replace '_GATE04D_C2R1_CANDIDATE$', ''
        $fileStem = $fileStem -replace '^K01-[PB]-\d{3}_', ''
        $description = ($fileStem -replace '_', ' ').Trim()
    }

    $swMaterial = [string]$r.solidworks_material
    if ([string]::IsNullOrWhiteSpace($swMaterial) -and ($r.PSObject.Properties.Name -contains "SolidWorksMaterial")) {
        $swMaterial = [string]$r.SolidWorksMaterial
    }

    $materialRelease = "UNCONTROLLED"
    if ($canonical -in @("K01-P-003","K01-P-007")) { $materialRelease = "RELEASED_316L" }
    elseif ($canonical -eq "K01-P-006") { $materialRelease = "CAD_ASSIGNED_316L / RELEASE_OPEN" }
    elseif ($canonical -eq "K01-P-014") { $materialRelease = "OPEN" }
    elseif ($canonical -eq "K01-P-015") { $materialRelease = "PPS_OBSERVED / PRODUCTION_GRADE_OPEN" }

    $rows += [pscustomobject]@{
        PartNo                 = $canonical
        Qty                    = if ($r.PSObject.Properties.Name -contains "qty") { $r.qty } else { $r.Qty }
        Unit                   = if ($r.PSObject.Properties.Name -contains "qty_unit") { $r.qty_unit } else { $r.Unit }
        Description            = $description
        DescriptionSource      = if ([string]::IsNullOrWhiteSpace([string]$r.description)) { "FILENAME_DERIVED_REVIEW_ONLY" } else { "CUSTOM_PROPERTY" }
        SolidWorksMaterial     = $swMaterial
        MaterialReleaseStatus = $materialRelease
        Configuration          = if ($r.PSObject.Properties.Name -contains "configuration") { $r.configuration } else { $r.Configuration }
        Path                   = $path
        SourceIdentity         = $raw
    }
}

$outJson = Join-Path $RepoRoot "bom\K01_BOM_NORMALIZED_CURRENT.json"
$outCsv  = Join-Path $RepoRoot "bom\K01_BOM_NORMALIZED_CURRENT.csv"

$report = [pscustomobject]@{
    schema       = "k01.bom_normalized_review.v1"
    created      = (Get-Date).ToString("o")
    status       = "REVIEW_BOM_AVAILABLE"
    source       = $source
    row_count    = $rows.Count
    rows         = $rows
    policy       = "This is a normalized review BOM. Filename-derived descriptions and uncontrolled materials are not release authority."
}

$report | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $outJson -Encoding UTF8
$rows | Export-Csv -LiteralPath $outCsv -NoTypeInformation -Encoding UTF8

Write-Host "BOM normalized: rows=$($rows.Count)"
Write-Host "JSON: $outJson"
Write-Host "CSV : $outCsv"
exit 0
