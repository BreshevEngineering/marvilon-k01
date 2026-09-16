# Marvilon Drawing Presentation Engine v1

Status: EXPERIMENTAL / DEFERRED FOR K01 CLOSURE.

The generic semantic core and placement roundtrip are already runtime-proven. Further presentation automation is not a release prerequisite. The controlled default is generated semantic drawing + placement replay + manual visual finish + human D8 approval. Resume presentation automation only when repeated manual layout effort demonstrates clear ROI.

## Purpose

The semantic Drawing System is already generic across K01-D-003 and K01-D-006. Presentation Engine v1 starts only after semantic authoring passes. It must never change engineering values, datum meaning or GPS semantics.

## Phase A

Phase A is intentionally conservative. It captures named semantic presentation evidence from the SLDDRW and performs checks that can be made deterministically in SOLIDWORKS 2018:

- required semantic annotations are present exactly once;
- drawing-view outlines stay inside sheet margins;
- drawing views do not enter the title-block reserved region;
- named annotation positions are captured in sheet coordinates;
- leader count/style/leader points are captured where the API exposes them;
- note text extents are captured using `INote.GetExtent()`;
- long semantic leaders and note/title-block collisions are warnings.

Phase A does **not** claim full visual QA. In particular, dimensions and GTols do not yet have a generalized exact text bounding-box collision model; leader bend points cannot be assigned arbitrarily by the API; and D8 readability remains a human approval.

## Leader API boundary

SOLIDWORKS 2018 exposes leader count, style and points on `IAnnotation`. For annotation kinds that support it, the leader attachment point can be set by index. The API documentation also states that leader coordinates are computed from annotation text and attachment points; therefore exact arbitrary polyline replay must not be claimed. Future replay will restore deterministic attachment/style where supported and then re-audit the resulting geometry.

## Progression

1. Phase A: evidence + hard-boundary audit.
2. Phase B: supported leader attachment/style replay from controlled presentation profile.
3. Phase C: collision-aware placement regions and title-block/template layer.
4. D003 + D006 regression.
5. D8 human visual approval remains final.


## 2026-09-16 stop decision

Workstation evidence established that the capture path can open and inspect generated drawings, resolve all required D003 views, capture 3/3 views and 28 annotations, and clean up its own SolidWorks process. The D003 post-processing failure was a UTF-8 BOM decoding defect in the Python audit layer, not a drawing-authoring failure.

D006 reached the presentation capture stage but stopped on `D006-J2-RA08`: the semantic author successfully created the Ra 0.8 surface-finish symbol, but that symbol does not currently receive/recover the same semantic annotation name used by the presentation scanner. This is a presentation-evidence gap, not a semantic-core regression.

Decision: do not spend further K01 closure time making Phase A exhaustive. Keep the implementation as experimental evidence. Manual visual finish is permitted and expected. No engineering value may be retyped manually; the manual step is limited to layout/readability.
