# K01 Human-Error Control Policy — HEC-001 v1

Complete elimination of human error is not physically achievable. MEDTAS is
designed so that a single forgotten action or memory lapse cannot silently become
a released configuration.

## Controls

1. Fail closed: missing evidence/material/reference = HOLD, never assumed PASS.
2. Stable CAD write protection: automation builds candidate copies first.
3. Atomic promotion: coupled parts/interfaces promote together.
4. Every critical parameter has one editable owner.
5. Every released value has machine readback from its consuming artifact.
6. Dependency graph propagates STALE after a change.
7. No manual BOM as authority.
8. No copied calculation result without input/configuration fingerprint.
9. Every EDR names alternatives and rejected options.
10. Every important engineering claim links to source/evidence.
11. Every CI has history in a dossier; superseded states are retained.
12. Every release has immutable hashes.
13. Git/PDM records who/when/why; no untracked production-source scripts.
14. Two-person approval is required later for Class-A decisions and production release.
15. Automated CI checks shall verify schemas, links, required fields and stale evidence.
16. Measurement/test evidence shall record instrument/calibration/conditions when relevant.
17. Supplier-critical data shall be lot/datasheet specific, not copied from generic catalogs.
18. Cross-version CAD migration requires clone + compare + rollback.
19. Physical assembly/service instructions shall contain poka-yoke and inspection points.
20. Exceptions require explicit waiver/deviation record with expiry/review condition.

## Target

The engineer should make engineering judgments. The system should remember,
propagate, compare, audit, block and document.
