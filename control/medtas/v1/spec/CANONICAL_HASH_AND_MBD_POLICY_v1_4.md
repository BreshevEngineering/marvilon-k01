# K01 MEDTAS Canonical Hash + MBD Policy v1.4

## 1. Native CAD binaries are not semantic state

`SLDPRT` / `SLDASM` binary SHA-256 is **not** an engineering freshness key. Native files can change on save because of internal IDs, caches, timestamps or serializer state without any change in geometry or product definition.

Therefore:

- `STATE_HASH` is computed from canonical semantic JSON only.
- `ARTIFACT_HASH` is computed from the exact generated evidence/artifact files.
- native CAD binary hashes are not included in the CAD semantic snapshot and do not propagate staleness.
- the optional save-invariance test may record native binary SHA only as a diagnostic demonstration; it never affects the verdict.

## 2. Canonical JSON rules

The semantic layer must:

1. sort object keys;
2. normalize floating-point values to 12 significant digits;
3. normalize signed zero;
4. exclude absolute paths, export timestamps, native binary hashes, document/software revision and machine/user metadata;
5. retain semantic identifiers, configurations, feature suppression, dimensions, datums, mates, component transforms, material assignments and geometry signatures.

### Mandatory invariance test

With no semantic edits:

1. export canonical state;
2. save the native assembly twice;
3. export canonical state again;
4. require both canonical payload hash and MEDTAS `STATE_HASH` to be identical.

Command: `06_TEST_CAD_HASH_INVARIANCE.cmd`.

If this test fails, canonicalization is incomplete and freshness logic is not release-eligible.

## 3. STEP normalization

STEP header information (`FILE_NAME`, timestamp, author/application metadata) is not engineering geometry. `step_canonical_hash_v1_4.py` removes volatile header content and retains `FILE_SCHEMA` before hashing.

This normalized STEP hash is an **artifact-stability** hash, not a proof of geometric equivalence. Entity IDs/order can still differ between equivalent exports. Geometry semantic identity remains governed by the CAD semantic snapshot / geometry signatures.

## 4. MBD / DimXpert policy

Production size tolerances, GD&T and datum definitions should migrate from independent drawing text into native model-based definition when practical.

MEDTAS extracts:

- DimXpert annotation identity/type;
- nominal size;
- upper/lower limits when available;
- datum identifier;
- model feature association;
- inspection/statistical/free-state flags;
- DimXpert feature identity and face count.

Node: `K01.MBD.A001`.

Until model PMI is fully authored, existing controlled tolerance seeds may remain as screening fallback, but this condition is explicit `PASS_WITH_LIMITATIONS`, never a silent second source of truth.

## 5. Tolerance analysis

`K01.TOL.A001` uses source priority:

1. native MBD / DimXpert;
2. controlled legacy seed only for unported chains.

Worst-case and Monte Carlo calculations are allowed only when contributor limits/distributions are explicitly bound. MEDTAS does not guess a distribution to make a chain pass.

Monte Carlo uses a deterministic seed for reproducibility.

## 6. Drawing role

The released drawing is a derived presentation of native CAD + MBD + verified tolerance state. It must not independently redefine dimensions/tolerances already governed by the model.

This is the basis for the existing prohibition on automatic dimension dumping.
