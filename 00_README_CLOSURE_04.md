# K01 Module Closure 04

Extract directly into:

`D:\BreshevEngineering\marvilon-k01\`

Run:

`04_RUN_K01_MODULE_CLOSURE.cmd`

This package does not redesign MEDTAS.

It fixes the Closure 03 launcher failure by invoking the controlled PowerShell closure script directly and by checking that every required path exists.

It also applies the design-authority decision that the existing CFD result of 50-55 degC is sufficient for the current J2 mechanical/seal thermal basis, with 55 degC used as design maximum.

Expected result:
- T03 closed;
- P006 material = AISI 316L / EN 1.4404 released;
- J2 qualification pressure = -0.20 ... +0.20 bar released;
- J2 thermal basis = CFD 50-55 degC released;
- T04 design seal baseline = 16x1.5 FKM 75A, existing gland retained;
- P006 drawing probe attempted;
- FEMM screening input pack built;
- module closure status generated;
- Git cleanup plan generated READ ONLY.

No files are deleted, moved, staged or committed by this package.
