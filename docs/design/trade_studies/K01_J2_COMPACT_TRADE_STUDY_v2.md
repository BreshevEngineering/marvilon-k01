# K01 J2 Compact Flange Study v2 — C2 selected for native CAD study

## Controlled next baseline — Gate04D-C2

- P003/P007 material: 316L / 1.4404
- flange: **round Ø33**
- fasteners: **3×M2.5**
- PCD: **26.5 mm**
- P007 flange thickness: 3.0 mm
- P003 J2 zone: 5.0 mm
- pilot: Ø14.10 H7/g6
- pilot male L1.50 / female depth1.70 / nominal bottom clearance0.20
- seal architecture: current 16×1.5, gland ID16.00 × W2.10 × D1.10
- P007 OAL: 35 mm

This is a **study baseline**, not production release.

## Why C2 before a three-lobed flange

C2 removes 3 mm from the full circular diameter while preserving the most
manufacturable topology: turning + drilling/tapping. A three-lobed flange adds
profile machining, more inspection and local stress transitions. C3 remains an
option only if C2 still fails the package objective.

## Geometry screen

C2 inner ligament:

`(26.5 - 2.9 - 20.6)/2 = 1.50 mm`

C2 outer ligament:

`(33.0 - 26.5 - 2.9)/2 = 1.80 mm`

These are study values. EDS-001 now requires actual local strength, thread,
seal, thermal, service and manufacturing evidence before release.

## Fastener material screening

Metric coarse tensile stress-area screen:
- M2.5×0.45: As ≈ 3.391 mm²
- M3×0.5: As ≈ 5.031 mm²

Using 450 MPa only as an A4-70 proof-stress screening value:
- M2.5 ≈ 1526 N per screw
- M3 ≈ 2264 N per screw

Previously calculated external pressure reaction = 3.1225 N. It is only
≈ 0.068% of the combined 3×M2.5 proof-load screen.

Therefore pressure reaction is not the fastener-sizing driver. Governing gates are
seal/preload, thread stripping, flange bearing/bending, galling, thermal preload
and service robustness.

## Evidence links

- EDR-003: clamp/fastener/pattern
- EDR-004: seal/gland
- EDR-005: flange geometry
- EDR-017: stainless fastener/galling
- CI-J2 dossier
- SRC-K01-ROTH-001
- SRC-K01-MOSS-001

## Gate04D-C2 acceptance before any production promotion

1. Native candidate geometry PASS.
2. P003/P007 material readback = 316L/1.4404.
3. P007 L35 unchanged.
4. Pilot/gland unchanged.
5. 3×M2.5 pattern at PCD26.5.
6. P007 clearance geometry Ø2.9.
7. Assembly controlled mates PASS.
8. No new hard interference.
9. Tool/head/service envelope PASS.
10. Thread/flange/seal mechanical gates PASS.
11. Thermal/service/galling disposition.
12. P007 structural refresh.
13. Technology + inspection plan update.
14. BOM availability check.
