# MARVILON K01 — MEDTAS Core Refactor

Extract directly into:

`D:\BreshevEngineering\marvilon-k01\`

This is an additive refactor. It does not delete historical v8 files, CAD, reports or the event history.  
The **primary runtime filenames no longer carry version suffixes**. Git is the software history.

## Start

1. `00_MEDTAS_PREFLIGHT.cmd`
2. `control\command_center\OPEN_K01_COMMAND_CENTER.cmd`

Do not use the old `OPEN_K01_COMMAND_CENTER_V8.cmd` after this migration.

## What changes

### First-class requirements
`control\requirements\requirements.json`

The pressure/temperature/media/service gaps are explicit requirements.  
A linked gate cannot PASS while a requirement is OPEN/PARTIAL/CANDIDATE/REJECTED.

### Hash-based evidence freshness
`control\provenance\REGISTER_EVIDENCE.ps1`
`control\provenance\VERIFY_PROVENANCE.ps1`

Every registered evidence item records:
- output SHA-256;
- every input SHA-256;
- tool name/version;
- tool-script SHA-256.

STALE becomes an arithmetic comparison, not an mtime judgement.

For the current C2R1 evidence, run once:

`control\provenance\BACKFILL_C2R1_PROVENANCE.cmd`

### Append-only event ledger
`control\events\engineering_events.jsonl`

New events include `previous_hash` and `event_hash`.  
`VERIFY_LEDGER.ps1` detects retrospective modification.

### State reducer
Engineering state is no longer computed in HTML:
- `control\state\reducer_core.ps1`
- `control\state\reducer.ps1`
- `tests\run_reducer_tests.ps1`

### Stable UI split
- `control\command_center\index.html`
- `styles.css`
- `app.js`
- `core.ps1`
- `server.ps1`

The primary UI has only five pages:
1. Overview
2. Requirements
3. Technical Filter
4. Product Definition
5. Files & Git

Work packages/dossiers remain evidence objects accessible from Files, not primary UI navigation.

### No engineering values in UI
CI rejects controlled project values hard-coded in HTML/JS.

### POST actions
All state-changing/external actions use HTTP POST. GET endpoints are read-only.

### BOM
A BOM is displayed/refreshed even when metadata has HOLDs.  
Metadata projection is not a prerequisite for having a BOM.

### Drawings
Drawing V3 is explicitly rejected for production release.  
The next drawing system is a TPD compiler based on:
requirements → released CAD → datum scheme → tolerance stack → Drawing Definition → native SOLIDWORKS drawing → semantic + visual QA.

### Configuration / revision control
`control\configuration\revision_policy.json`

Released artifacts are immutable. Changes create a successor revision/baseline.

### GitHub CI
`.github/workflows/k01-control-ci.yml`

CI checks:
- JSON Schema;
- requirement-to-gate links;
- reducer tests;
- absence of controlled engineering numbers in UI.

SolidWorks itself remains outside GitHub CI.

## Engineering priority

This refactor is intended to reduce infrastructure work, not expand it.

The K01 line remains:
Gate04E P006 → pressure/media requirements → T04/T05 → T06/T07 → BOM/TPD → FEMM → bench → atomic A001 release.
