# K01 active engineering sequence

## Closed — do not restart without a dependency-changing reason
1. Identity Freeze.
2. Assembly Approval Stage A.
3. Moving-group proof / Assembly Stage B.
4. Gate04B M4 pattern and Datum-C candidate design.
5. K01-BASELINE-02C Datum-C producer correction and candidate assembly integration — PASS.

## Active line — Baseline-02C controlled canonical promotion
1. Freeze checkpoint/evidence/product delta.
2. Run read-only Baseline-02C promotion preflight.
3. Review the **applicable existing stable-promotion source** before any write.
4. Archive pre-promotion canonical CAD and hashes.
5. Apply reference-safe stable-identity promotion.
6. Reopen canonical A001 and generate a fresh native semantic export plus semantic/assembly verification.
7. Regenerate canonical engineering snapshot from that promoted state.
8. Recompute dependency/freshness state.
9. Rebuild EBOM/MBOM from the fresh semantic occurrence tree and prove 14 modeled occurrences + K01-P-017 qty=1.
10. Git checkpoint and rebuild the current AI handoff.

## Important toolchain finding
`tools/sw_gate04b_close_datum_c.py` in the supplied toolchain is an older radial-slot candidate builder and must not be executed for current EDR-023.
`tools/medtas/final_assembly_promotion_v2_2.py` is a final-candidate/R01 Pack-and-Go route, not the current stable Baseline-02C promotion.
The earlier atomic stable-promotion precedent `scripts/K01_PROMOTE_P003_P007.py` must be reviewed and reused/adapted if appropriate.

## After P0 promotion
Resume P1-P3 blockers in dependency/critical-path order.

## Drawing program
After applicable P0-P3 inputs are controlled:
1. P007/K01-D-006 native Product Characteristics + DimXpert/PMI.
2. Tolerance/inspection binding.
3. One professional native drawing exemplar.
4. Semantic lint + visual QA + manufacturer feedback.
5. Reuse the verified drawing pipeline for D003/D005/D012 and future parts.

## Session rule
Every step is checked against current checkpoint, authority map, P0-P6, dependency/freshness state and technical filter before mutation.

Handoff source coverage for the active line is controlled by `control/project/K01_HANDOFF_REQUIRED_SOURCES_CURRENT.json`.
