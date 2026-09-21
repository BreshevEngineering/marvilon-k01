# K01 Native Attachment QA V1 — add-only capability

This directory is deliberately self-contained.

It does **not** edit:
- `K01_SOLIDWORKS_DRAWING_API_STANDARD_CURRENT.txt`
- `K01_SOLIDWORKS_API_PROVEN_REGISTRY_v1.json`
- root `README.md`
- current builder source
- runtime core
- BUILD or REFINE sources

Those existing files are left untouched because the repository currently contains
some proven-bundle documents as untracked filesystem files. Their Git normalization
is a separate repository task and is not allowed to block this engineering WIP.

## What V1 does

Read-only inventory:
- drawing view name;
- referenced model path;
- semantic annotation name;
- `IAnnotation.GetAttachedEntities2()`;
- `IAnnotation.GetAttachedEntityTypes()`;
- dangling state;
- cylinder diameter/center-X signature for attached face/edge geometry.

Read-only verification:
- exact annotation name;
- expected view;
- expected referenced model path;
- attachment present and not dangling;
- `ATTACHMENT_PRESENT` or `CYLINDER_DIAMETER` signature.

The exact source drawing must be closed. Unrelated SOLIDWORKS documents may remain open.
