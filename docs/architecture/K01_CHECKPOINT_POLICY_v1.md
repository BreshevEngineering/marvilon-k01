# K01 checkpoint policy

A checkpoint freezes transition evidence. It is not a second source of geometry or product truth.

Every major transition shall record:
- checkpoint ID/type;
- previous and next maturity/authority state;
- exact evidence paths/hashes where available;
- affected product identities;
- technical-filter disposition;
- dependency/stale impact;
- material state of affected parts;
- BOM/DimXpert/drawing/inspection impact;
- rollback boundary for mutations;
- Git/handoff checkpoint when closed.

A checkpoint is invalid if it says PASS without evidence, hides OPEN material/process/test requirements, promotes screening evidence to release evidence, or cannot identify the source/executor used for a mutating step.

Current CP-C:
`control/project/K01_CHECKPOINT_CURRENT.json` -> `control/checkpoints/K01-CP-20260910-BASELINE-02C-DATUM-C-VERIFIED.json`.

The next CP-P must contain pre/post canonical hashes, backup manifest, post-promotion semantic/assembly QA, new snapshot, stale reduction, EBOM proof (`14 occurrences`, `K01-P-017 qty=1`) and Git/handoff evidence.

## Storage pattern

- Immutable checkpoints: `control/checkpoints/<checkpoint-id>.json`
- Current pointer: `control/project/K01_CHECKPOINT_CURRENT.json`
- Git preserves changes to both; handoff packs both.
- A new checkpoint never overwrites an old checkpoint file; it adds a new immutable record and moves only the current pointer.
