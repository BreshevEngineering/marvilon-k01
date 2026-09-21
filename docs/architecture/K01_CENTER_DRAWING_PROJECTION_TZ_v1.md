# K01 Center — Drawing Projection Control TZ v1

The Center remains a derived control surface. It must not author Product Definition or drawing semantics.

For every drawing artifact, show one compact **Drawing Projection** panel with:

- drawing ID / part ID;
- compiled Product Definition fingerprint consumed by the drawing;
- MEDTAS node state for the drawing projection;
- semantic projection coverage `projected safe Cxx / safe Cxx`;
- carrier split: native drawing semantic carriers vs `PROJECTION_FALLBACK` carriers;
- visual QA state;
- drawing release readiness;
- source SLDDRW seed + source-invariance result;
- current candidate SLDDRW/PDF/BMP paths and SHA-256;
- exact stale reason when any consumed upstream state hash changes.

Required interpretation:

- `semantic projection PASS` means every safe Product Characteristic is represented from the compiled contract. It does **not** mean manufacturing release.
- `PROJECTION_FALLBACK` is allowed for an editable design-review base drawing when SW2018 cannot create the desired native carrier in a bounded automation attempt. It must remain visibly classified and cannot satisfy release-native-carrier requirements by itself.
- `visual QA PENDING` prevents professional-drawing completion but does not erase semantic projection evidence.
- `DRAWING_RELEASE_READY=HOLD` always dominates release even if the SLDDRW/PDF looks complete.

When Product Definition, CAD binding, interface state, or PMI context changes, the authoritative DAG must stale `K01.DRAWING.D006.PROJECTION`. The Center may offer the registered rebuild action, but may not clear stale state manually.
