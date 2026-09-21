# Dispatcher capability contract

The existing dispatcher should implement `--list --json` directly from its own
command registry. Listing must be read-only, produce JSON only on stdout, and
return nonzero on failure. Do not maintain a second command mapping in the Center.

```json
{"schema":"k01.commands.v1","commands":[{"id":"audit","argv":["audit"],"center_enabled":true}]}
```

This is an interface example, not a claim that audit exists in the current CLI.
The Center executes only explicitly enabled entries through the same dispatcher.
This edition accepts simple alphanumeric argument tokens, dots, dashes and underscores.
Parameter entry and CAD-changing command workflows need separate integration.

# Upstream requirements contract and implementation order

1. Inventory requirements already present in the current repository; do not create a
   competing authority. The diagnostics alone do not prove no registry exists.
2. Assign each requirement a stable ID, revision, statement, quantity and unit,
   operating case, acceptance criterion, source document and exact location,
   justification, approval state, responsible person, and verification method.
3. Record assumptions separately from approved requirements and derived loads.
4. Link each calculation input to the requirement/assumption ID and revision used.
5. The engine validates these links and reports missing/changed inputs. The Center
   displays the resulting evidence; it does not approve requirements.

Transport: `k01.requirements.v1` with a `requirements` array. Each record should
carry the fields above plus source evidence links and a reported status.
Do not publish an empty or populated draft as an approved registry.

# 300 N traceability issue

The supplied historical file
`reports/medtas/snapshot/current/K01_CANONICAL_ENGINEERING_SNAPSHOT_A001_v1.json`
contains both `normal_force_N: 300.0` and `preload_N_each: 300.0`.
These represent distinct load inputs and must not be merged into one requirement.
The supplied bolt-equivalence report also records that connector/preload equivalence
for three M2.5 fasteners at 300 N each is not approved.

Record both as observed calculation inputs with justification OPEN until their
origin, load case, derivation and acceptance are established. A solved load case
does not itself demonstrate that the load is a correct product requirement.
This package does not change their values, rerun the calculation, or approve them.


# Executable engineering-chain object taxonomy (V11)

The current K01 chain distinguishes the following object classes and they MUST NOT be collapsed:

1. **Requirement / interface envelope** — upstream need and acceptance intent.
2. **Requirement allocation** — explicit assignment/budget/complementary responsibility to system, interface, part or characteristic.
3. **Engineering decision** — selected architecture with rationale/technical-filter evidence.
4. **Derived engineering input** — calculated/screening load, force, limit or intermediate value with its own quantity identity, derivation/status and consumers.
5. **Product Characteristic** — controlled/PARTIAL/OPEN product definition including nominal/variation, datum/reference system, measurement condition, material/surface/process, inspection strategy and configuration/effectivity.
6. **CAD/PMI binding** — deterministic semantic binding plus binding-invariance qualification.
7. **Physics evidence** and **variation/capability evidence** — separate invalidation domains.
8. **Compiled Product Definition domain slices** — drawing, variation, inspection, physics, manufacturing and configuration fingerprints.
9. **Drawing projection** and **inspection realization** — downstream projections/records, never upstream authorities.
10. **Released configuration/effectivity** — immutable released revision/baseline with exact evidence hashes.

Downstream inability to manufacture, inspect, analyze or project does not silently edit a characteristic. It creates an Engineering Feedback Record (EFR) and reopens the relevant decision/change under pre-change impact control.

Current authorities: `control/project/K01_ENGINEERING_EXECUTION_CONTRACT_CURRENT.json`, `control/product_definition/K01_PRODUCT_DEFINITION_POLICY_CURRENT.json`, `control/requirements/K01_REQUIREMENT_ALLOCATION_REGISTRY_v1.json`, and `control/engineering/K01_DERIVED_ENGINEERING_INPUTS_v1.json`.

## Drawing pipeline D1-D9 contract (V11.1)

Center must distinguish the V10 design-review base from the release-native D1-D9 lane. Show claim-level D1 authoring tasks, D2 mutation gate, D3 binding/annotation-view verification, D4 release-native semantic fingerprint, D5 import method evidence, D6 semantic-invariance check, D7 semantic QA, D8 human visual approval and D9 export/effectivity.

`Why stale?` must cite the changed graph input/fingerprint. A claim's annotation-view role is visible context; BOM balloons and characteristic/inspection tags are separate identifiers. General tolerances/default roughness and STEP AP242/DXF delivery are conditional controlled policies, never assumptions.
