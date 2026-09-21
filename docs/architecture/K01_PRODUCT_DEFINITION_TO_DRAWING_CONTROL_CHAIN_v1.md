# K01 Product Definition → Drawing control chain v1

## 1. Purpose

K01 engineering data must flow in one direction: requirement/design intent → engineering decision/evidence → Product Characteristic → CAD semantic binding/PMI → drawing projection → inspection → release.

The drawing is not an independent design authority. It is a human-readable manufacturing/inspection projection of the controlled product definition.

## 2. Why this control exists

The P007/K01-D-006 work exposed a failure mode: the project had the correct high-level pipeline, but execution drifted into solving the drawing UI before the characteristic semantics were frozen. Legacy candidate tolerances (`±0.25`, `±0.05`, candidate GD&T values) could therefore reappear even though current engineering decisions treated them as OPEN.

This architecture prevents recurrence by making **Product Definition Readiness** a hard predecessor of drawing authoring.

## 3. Mandatory chain

```text
Requirement / interface envelope
        ↓
Engineering decision / technical filter / calculation
        ↓
Stable Product Characteristic ID (Cxx)
        ↓
Definition state:
  nominal + tolerance/fit/GD&T + material/process + OPEN/CONTROLLED
        ↓
Deterministic native CAD binding
        ↓
Native PMI / DimXpert / controlled model annotation
        ↓
Semantic readback + tolerance/variation analysis
        ↓
Compiled Product Definition fingerprint
        ↓
SLDDRW projection
        ↓
Drawing semantic QA + human visual QA
        ↓
Inspection characteristic / acceptance
        ↓
Release
```

## 4. Authority separation

There is no single magic file.

- `control/requirements/requirements.json` owns requirement statements/acceptance envelopes.
- engineering decisions/EDRs/calculations own justified choices and numeric closure evidence.
- canonical native CAD owns nominal modeled geometry only.
- Product Characteristic controls bind requirements/decisions to features.
- native PMI/DimXpert is the preferred semantic carrier for size/fit/GD&T.
- process/material registries own their domains.
- compiled Product Definition is a **derived contract** for downstream drawing/inspection, not a new authority.
- SLDDRW/PDF are derivative presentations.

## 5. Characteristic contract

Every manufacturing/inspection characteristic must expose:

- stable ID;
- part/node/interface;
- engineering function;
- category (SIZE, FIT, GD&T, MATERIAL, SURFACE_TEXTURE, PROCESS, ACCEPTANCE, etc.);
- nominal/requirement;
- allowable variation semantics;
- source requirement/decision/evidence;
- CAD binding and binding confidence;
- native semantic carrier;
- drawing projection rule;
- inspection method/acceptance;
- definition state (`CONTROLLED`, `PARTIAL`, `OPEN`, `NOT_APPLICABLE`);
- release-blocking flag.

`OPEN` is a valid state. It is never automatically replaced by a CAD/template/general tolerance.

## 6. Three separate readiness gates

### DRAWING_CANDIDATE_READY
Allows a design-review/base drawing when controlled nominals exist and unresolved semantics are explicitly OPEN. The drawing may contain `NOM`/OPEN callouts but no invented release values.

### PMI_AUTHORING_READY
Allows native PMI authoring only where deterministic CAD binding exists and the tolerance/fit/GD&T semantics to be authored are controlled. OPEN tolerances remain absent/OPEN.

### DRAWING_RELEASE_READY
Requires all release-blocking Product Characteristics and coverage categories closed, including functional tolerances, process definition, surface texture where required, inspection method/acceptance, semantic QA and visual QA.

## 7. Drawing compiler contract

A drawing generator/refiner may consume only the compiled Product Definition output. It may not:

- parse `candidate_spec` strings as released authority;
- infer tolerances from SOLIDWORKS defaults;
- create a dimension not mapped to a characteristic or explicit reference-only rule;
- promote `NOM` to released tolerance;
- use PDF/text as inspection acceptance authority.

Each projected annotation must retain `characteristic_id`, source fingerprint and projection method in machine evidence.

## 8. Drift prevention

A patch that changes execution strategy must atomically update:

1. `K01_NEXT_ACTIONS_CURRENT.json`;
2. relevant architecture/policy;
3. `docs/DECISION_LOG.md`;
4. `K01_EXECUTION_METHOD_REGISTRY_CURRENT.json`;
5. acceptance test/gate.

If these are not updated together, the implementation patch is incomplete.

Same mechanism failure budget: **2**. After two failures, implementation stops and architecture is reviewed. A rejected path cannot be revived under a new filename without new evidence.

## 9. P007 immediate disposition

Current P007 drawing-candidate semantics are controlled by `K01_P007_DEFINITION_DECISIONS_CURRENT.json` and the compiler. Legacy candidate values such as C05/C06 `±0.05`, C01 flatness `0.03`, C03 perpendicularity `0.03` and C04 position `0.15` are not release values unless re-justified and explicitly promoted through the Product Definition chain.

C02 `Ø14.10 H7` is the current controlled part-side fit semantic. C05 `Ø33.00` is nominal with release tolerance OPEN. Material is AISI 316L / EN 1.4404. Other OPEN items remain explicit blockers as listed by the compiler.
