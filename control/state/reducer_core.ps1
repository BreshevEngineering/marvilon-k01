function Get-K01RequirementCoverage($Requirements,$Filter){
    $rows=@()
    $gateMap=@{}
    foreach($g in @($Filter.gates)){$gateMap[[string]$g.gate]=$g}

    foreach($r in @($Requirements.requirements)){
        $linkedGates=@($r.links.gates)
        $linkedEvidence=@($r.links.evidence)
        $gateStates=@()
        foreach($gid in $linkedGates){
            if($gateMap.ContainsKey([string]$gid)){$gateStates += [string]$gateMap[[string]$gid].status}
            else{$gateStates += 'MISSING_GATE'}
        }
        $rows += [pscustomobject]@{
            id=[string]$r.id
            title=[string]$r.title
            statement=[string]$r.statement
            requirement_status=[string]$r.status
            verification_method=[string]$r.verification_method
            gates=$linkedGates
            gate_states=$gateStates
            evidence=$linkedEvidence
            covered_by_gate=($linkedGates.Count -gt 0 -and -not($gateStates -contains 'MISSING_GATE'))
            covered_by_evidence=($linkedEvidence.Count -gt 0)
            release_blocker=([string]$r.status -in @('OPEN','PARTIAL','CANDIDATE','REJECTED'))
        }
    }
    return $rows
}

function Get-K01ProvenanceStatus([string]$EvidencePath,[string]$RepoRoot){
    $prov=$EvidencePath+'.provenance.json'
    if(-not(Test-Path -LiteralPath $prov -PathType Leaf)){
        return [pscustomobject]@{status='UNHASHED';provenance_path=$prov;mismatches=@()}
    }
    $verify=Join-Path $RepoRoot 'control\provenance\VERIFY_PROVENANCE.ps1'
    if(-not(Test-Path -LiteralPath $verify -PathType Leaf)){
        return [pscustomobject]@{status='PROVENANCE_TOOL_MISSING';provenance_path=$prov;mismatches=@()}
    }

    $json=& $verify -ProvenancePath $prov -RepoRoot $RepoRoot 2>$null
    $code=$LASTEXITCODE
    try{
        $r=($json|Out-String)|ConvertFrom-Json
        return $r
    }catch{
        return [pscustomobject]@{status=if($code -eq 0){'CURRENT'}else{'STALE'};provenance_path=$prov;mismatches=@()}
    }
}

function Resolve-K01GateState($Gate,$CoverageRows,$EvidenceFreshness){
    $gid=[string]$Gate.gate
    $reqs=@($CoverageRows|Where-Object{$_.gates -contains $gid})
    $reqBlock=@($reqs|Where-Object{$_.release_blocker})

    if($reqBlock.Count -gt 0){
        return [pscustomobject]@{
            gate=$gid
            status='HOLD_REQUIREMENT'
            base_status=[string]$Gate.status
            reason=("Blocked by requirement(s): "+(($reqBlock|ForEach-Object{$_.id}) -join ', '))
            requirement_ids=@($reqBlock|ForEach-Object{$_.id})
        }
    }

    $stale=@($EvidenceFreshness|Where-Object{$_.gate -eq $gid -and $_.status -eq 'STALE'})
    if($stale.Count -gt 0){
        return [pscustomobject]@{
            gate=$gid
            status='STALE'
            base_status=[string]$Gate.status
            reason='At least one hash-bound evidence input changed.'
            requirement_ids=@()
        }
    }

    return [pscustomobject]@{
        gate=$gid
        status=[string]$Gate.status
        base_status=[string]$Gate.status
        reason=[string]$Gate.basis
        requirement_ids=@()
    }
}
