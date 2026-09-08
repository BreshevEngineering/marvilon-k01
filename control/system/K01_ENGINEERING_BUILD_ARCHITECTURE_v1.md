# K01 Engineering Build Architecture v1

Target command: `K01_ENGINEERING_BUILD`.

It will eventually execute:
1. read master and parameter registry;
2. read actual stable SOLIDWORKS assembly/components;
3. validate material/custom-property completeness;
4. CAD readback of controlled dimensions/interfaces;
5. dimensional-chain evaluation;
6. decision-record applicability/staleness check;
7. calculation-evidence freshness check;
8. automatic BOM generation;
9. technology completeness audit;
10. file-registry link/existence audit;
11. Git status / uncommitted control changes;
12. generate AI engineering context;
13. generate release-readiness report.

A changed design parameter shall automatically mark dependent evidence STALE.

Example: `J2 fastener M3 → M2.5` reopens flange geometry, ligament chain, fastener/thread check, P007 structural refresh, assembly/interference, BOM, drawing, technology route and EDR-003/005. FEMM impact is explicitly evaluated rather than assumed.
