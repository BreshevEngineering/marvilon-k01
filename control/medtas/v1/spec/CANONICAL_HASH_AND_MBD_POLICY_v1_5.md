# MEDTAS Canonical Hash + MBD Policy v1.5

## 1. Native CAD binary hashes

`.SLDPRT` / `.SLDASM` binary hashes are diagnostic provenance only. They never determine semantic freshness because a no-change native save can rewrite non-engineering binary state.

## 2. Semantic CAD hash

`STATE_HASH` consumes a canonical machine-readable snapshot. Canonicalization shall:

- sort object keys;
- sort collections whose order is not engineering-significant in the exporter/canonicalizer;
- normalize numbers to the controlled significant-digit policy;
- remove absolute paths, timestamps, machine/user names, export time, document revision noise and native binary hashes;
- retain component identity/configuration/suppression/transforms, mates, material, feature state, engineering dimensions, datums and geometric face signatures.

Qualification rule: two no-change native saves followed by two successful semantic exports must yield identical canonical payload hash and identical `STATE_HASH`.

## 3. STEP

The normalized STEP artifact hash removes volatile header identity/time fields. It is only an artifact-stability check. Geometric equivalence requires independent geometric signatures / mass properties / interface checks.

## 4. MBD / DimXpert

Native CAD + MBD/DimXpert is the preferred product-definition authority for tolerances, datums, inspection characteristics and GD&T. Tolerance analysis consumes MBD first. Controlled legacy seeds are temporary screening fallbacks only where native PMI has not yet been authored.

## 5. Drawing

A drawing is a derived human-readable representation of native CAD + MBD product definition. AutoDimension-style bulk dimension invention is prohibited. Missing definition remains OPEN and must not be invented during drawing generation.

## 6. BOM

CAD owns occurrence/quantity; controlled product metadata owns identity/description/material release/make-buy/supplier/lifecycle. BOM files are projections and are verified against the canonical BOM model.
