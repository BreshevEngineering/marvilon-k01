param(
    [string]$RepoRoot = "D:\BreshevEngineering\marvilon-k01"
)

$ErrorActionPreference = "Stop"

function Read-K01Json {
    param([string]$RelativePath)

    $path = Join-Path $RepoRoot $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing controlled input: $path"
    }

    return (Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Get-K01Requirement {
    param(
        $RequirementsDocument,
        [string]$RequirementId
    )

    $match = @(
        $RequirementsDocument.requirements |
        Where-Object { [string]$_.id -eq $RequirementId } |
        Select-Object -First 1
    )

    if ($match.Count -eq 0 -or $null -eq $match[0]) {
        throw "Requirement missing: $RequirementId"
    }

    return $match[0]
}

$build = Read-K01Json "reports\cad\current\K01_GATE04E_P006_SERVICE_BUILD.json"
$verify = Read-K01Json "reports\cad\current\K01_GATE04E_P006_SERVICE_VERIFY.json"
$bom = Read-K01Json "reports\bom\K01_BOM_RECONCILIATION_study_c2r1.json"

$requirementsPath = Join-Path $RepoRoot "control\requirements\requirements.json"
$requirements = Read-K01Json "control\requirements\requirements.json"

if ([string]$build.status -ne "PASS_CANDIDATE_BUILD") {
    throw "Gate04E build status is not PASS_CANDIDATE_BUILD."
}

if ([string]$build.schema -ne "k01_gate04e_p006_service_build_v3") {
    throw "Current Gate04E evidence is not corrected v3. Current schema: $($build.schema)"
}

if ([string]$verify.status -ne "PASS_P006_LINKED_IN_FULL_C2R1_ASSEMBLY") {
    throw "Gate04E full-assembly verification is not PASS."
}

$p006Rows = @(
    $bom.rows |
    Where-Object { [string]$_.part_no -eq "K01-P-006" } |
    Select-Object -First 1
)

if ($p006Rows.Count -eq 0 -or $null -eq $p006Rows[0]) {
    throw "P006 is missing from reconciled BOM."
}

$p006 = $p006Rows[0]

if (-not ([string]$p006.material_status).StartsWith("CONTROLLED")) {
    throw "P006 material is not CONTROLLED in reconciled BOM. Current: $($p006.material_status)"
}

if ([string]$p006.material_authority -notmatch "316L|1\.4404") {
    throw "P006 material authority is not AISI 316L / EN 1.4404. Current: $($p006.material_authority)"
}

# Backup requirements before any controlled write.
$historyDirectory = Join-Path $RepoRoot ("control\requirements\history\" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -Path $historyDirectory -ItemType Directory -Force | Out-Null
Copy-Item -LiteralPath $requirementsPath -Destination (Join-Path $historyDirectory "requirements.json") -Force

$reqP006 = Get-K01Requirement $requirements "REQ-K01-MAT-P006-001"
$reqP006.status = "RELEASED"
$reqP006.statement = "P006 production material shall be AISI 316L / EN 1.4404."
$reqP006.source = [pscustomobject]@{
    type = "controlled_bom_reconciliation"
    ref = "K01_BOM_RECONCILIATION_study_c2r1.json / K01-P-006"
}
$reqP006.verification_method = "Native SOLIDWORKS material readback + reconciled BOM + material certificate at manufacture"

$reqPressure = Get-K01Requirement $requirements "REQ-K01-ENV-DP-001"
$reqPressure.status = "RELEASED"
$reqPressure.statement = "J2/P007 qualification differential-pressure envelope shall be -0.20 ... +0.20 bar."
$reqPressure.source = [pscustomobject]@{
    type = "engineering_decision"
    ref = "EDR-021"
}
$reqPressure.verification_method = "Final P007 Static +0.20 bar; Buckling -0.20 bar; leak acceptance test"

$reqTemperature = Get-K01Requirement $requirements "REQ-K01-ENV-TEMP-001"
$reqTemperature.status = "RELEASED"
$reqTemperature.statement = "For the current release, accepted CFD establishes J2 local temperature at 50-55 degC; use 55 degC as design maximum."
$reqTemperature.source = [pscustomobject]@{
    type = "design_authority_accepted_CFD"
    ref = "K01 CFD result accepted 2026-09-05"
}
$reqTemperature.verification_method = "Existing CFD is the controlled thermal basis; reopen only after a controlled geometry/flow/thermal-boundary change"

$requirements |
    ConvertTo-Json -Depth 50 |
    Set-Content -LiteralPath $requirementsPath -Encoding UTF8

$decisionDirectory = Join-Path $RepoRoot "control\decisions"
New-Item -Path $decisionDirectory -ItemType Directory -Force | Out-Null

[pscustomobject]@{
    schema = "k01.edr.v1"
    id = "EDR-021"
    title = "J2 differential-pressure qualification envelope"
    status = "DECIDED"
    decision = "Use -0.20 ... +0.20 bar as the structural/sealing qualification differential-pressure envelope. This is not a normal-operating-pressure claim."
    basis = @(
        "Containment-system maximum inlet pressure is 200 mbar in the protection concept.",
        "Known outlet suction is approximately -100 mbar; -0.20 bar provides conservative negative-side qualification.",
        "The 6 bar probe-purge path is diverted away from the optical sensor module.",
        "Existing P007 +0.20 bar static and -0.20 bar buckling cases are retained and refreshed on final geometry."
    )
} |
    ConvertTo-Json -Depth 20 |
    Set-Content -LiteralPath (Join-Path $decisionDirectory "EDR-021_J2_DIFFERENTIAL_PRESSURE_ENVELOPE.json") -Encoding UTF8

[pscustomobject]@{
    schema = "k01.edr.v1"
    id = "EDR-022"
    title = "J2 CFD thermal basis"
    status = "DECIDED"
    decision = "Accept existing CFD 50-55 degC as sufficient current J2 thermal evidence; use 55 degC as design maximum."
    reopen_condition = "Controlled geometry, flow, cooling or thermal-boundary change."
} |
    ConvertTo-Json -Depth 20 |
    Set-Content -LiteralPath (Join-Path $decisionDirectory "EDR-022_J2_CFD_TEMPERATURE_BASIS.json") -Encoding UTF8

$workPackageDirectory = Join-Path $RepoRoot "control\workpacks"
New-Item -Path $workPackageDirectory -ItemType Directory -Force | Out-Null

[pscustomobject]@{
    schema = "k01.workpackage_closeout.v1"
    id = "T03"
    title = "Pilot tolerance chain + P006 service drive"
    status = "PASS_T03"
    engineering_definition = "PASS"
    cad_implementation = "PASS"
    material = "AISI 316L / EN 1.4404"
    evidence = @(
        "reports/cad/current/K01_GATE04E_P006_SERVICE_BUILD.json",
        "reports/cad/current/K01_GATE04E_P006_SERVICE_VERIFY.json",
        "reports/bom/K01_BOM_RECONCILIATION_study_c2r1.json"
    )
    residual_to_T06 = "Repeated service-cycle / galling qualification"
} |
    ConvertTo-Json -Depth 20 |
    Set-Content -LiteralPath (Join-Path $workPackageDirectory "K01_T03_CLOSEOUT_CURRENT.json") -Encoding UTF8

$reducer = Join-Path $RepoRoot "control\state\reducer.ps1"
if (Test-Path -LiteralPath $reducer -PathType Leaf) {
    & $reducer -RepoRoot $RepoRoot | Out-Null
}

Write-Host ""
Write-Host "PASS T03: P006 service CAD + full assembly + 316L material."
Write-Host "PASS pressure requirement: -0.20 ... +0.20 bar qualification envelope."
Write-Host "PASS temperature requirement: accepted CFD 50-55 degC, Tmax=55 degC."
exit 0
