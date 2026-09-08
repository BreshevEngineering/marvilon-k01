# K01 Module Closure 05

Extract directly into:

`D:\BreshevEngineering\marvilon-k01\`

Run:

`05_RUN_K01_MODULE_CLOSURE.cmd`

## Why Closure 04 stopped

Closure 04 correctly refused to close T03 because the current Gate04E report was still the older `k01_gate04e_p006_service_build_v2` evidence with `front_plane_x_mm = 1000`.

That 1000 mm value is not a physical P006 dimension. In the v2 instrumentation the normal component of `Surface.PlaneParams` was treated as a coordinate and multiplied by 1000.

Closure 05 includes the corrected v3 Gate04E builder and ALWAYS reruns it first. The closure then requires v3 evidence.

T03 acceptance itself is based on the functional evidence:
- native service feature exists in the candidate;
- stable P006 is not modified;
- candidate links into the full C2R1 verification assembly;
- controlled P006 material is 316L / 1.4404.

The diagnostic coordinate is not used as a functional release characteristic.

## CFD temperature

Per design-authority decision, the existing 50-55 degC CFD result is accepted. No new thermal study is added now. 55 degC is used as the current design maximum.

## T05

Closure 05 adds a deterministic analytical screen for:
- OD33 / PCD26.5 packaging ligaments;
- +/-0.20 bar separating force;
- 3 x M2.5 candidate clamp preload;
- prior thread-strip screen;
- prior local flange-bending screen;
- conservative FKM compression-force bound.

This is not yet final torque release. It is intended to determine whether the compact flange remains viable before local FEA and service/galling qualification.

## Repository

No cleanup, delete, stage or commit is performed here. File consolidation waits until the engineering checkpoint after T05/T07.
