$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $repo 'control\state\reducer_core.ps1')

$fail=0
function AssertEq($actual,$expected,[string]$name){
    if([string]$actual -ne [string]$expected){
        Write-Host "FAIL $name expected=$expected actual=$actual" -ForegroundColor Red
        $script:fail++
    }else{Write-Host "PASS $name"}
}

$requirements=[pscustomobject]@{requirements=@(
    [pscustomobject]@{
        id='REQ-K01-TEST-001';title='test';statement='test';status='OPEN';verification_method='test';
        links=[pscustomobject]@{gates=@('static_strength_contact');evidence=@();design_objects=@()}
    }
)}
$filter=[pscustomobject]@{gates=@(
    [pscustomobject]@{gate='static_strength_contact';status='PASS';basis='base'}
)}
$coverage=@(Get-K01RequirementCoverage $requirements $filter)
$resolved=Resolve-K01GateState $filter.gates[0] $coverage @()
AssertEq $resolved.status 'HOLD_REQUIREMENT' 'OPEN requirement blocks nominal PASS gate'

$requirements.requirements[0].status='RELEASED'
$coverage=@(Get-K01RequirementCoverage $requirements $filter)
$fresh=@([pscustomobject]@{gate='static_strength_contact';status='STALE'})
$resolved=Resolve-K01GateState $filter.gates[0] $coverage $fresh
AssertEq $resolved.status 'STALE' 'changed hash makes gate STALE'

$fresh=@([pscustomobject]@{gate='static_strength_contact';status='CURRENT'})
$resolved=Resolve-K01GateState $filter.gates[0] $coverage $fresh
AssertEq $resolved.status 'PASS' 'released requirement + current evidence preserves base gate'

if($fail -gt 0){Write-Host "$fail test(s) failed" -ForegroundColor Red;exit 2}
Write-Host "All reducer tests passed."
exit 0
