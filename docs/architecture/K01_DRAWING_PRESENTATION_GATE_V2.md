# K01 Drawing Presentation Gate v2

Status: controlled drawing workflow correction, 2026-09-16.

## Problem captured by K01-D-004 first trial
The generic semantic engine correctly created two views and three nominal dimensions, but its raw candidate had unacceptable presentation: weak sheet use, note overlap, scale/title-block mismatch, and loss of Ø5.055 precision. Therefore semantic authoring PASS must never be interpreted as finished-drawing/D8 PASS.

## Frozen rule
The accepted D003/D006 level is preserved by `K01_DRAWING_GOLDEN_RECIPE_CURRENT.json`. New candidate manifests produced by the generic engine carry `presentation_status=HOLD_NOT_VERIFIED`; Drawing Control must not publish such a candidate. A presentation/manual-finish/exemplar stage must explicitly reach a `PASS_*` presentation state. Legacy D003/D006 candidates without this field remain grandfathered by their already accepted evidence.

## Precision
`AnnotationSpec.precision` is an explicit decimal-place override. It is used when geometry requires more than the generic 2-decimal default, e.g. P004 Ø5.055.

## D004 recovery
D004 uses a dedicated fixed presentation recipe derived from the accepted D006 layout discipline: A3, first angle, 10:1, two functional views, concise notes in the lower-left information zone, no invented tolerance/datum/GPS/surface-texture values. The native candidate remains release-HOLD until upstream Product Definition closes.
