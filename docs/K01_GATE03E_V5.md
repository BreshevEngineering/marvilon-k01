# K01 Gate03E — v5 interface geometry

Gate03D measured the actual P006 geometry from the production assembly:

- P006 axial span relative to P003 rear: -6.000 ... +2.000 mm
- cylindrical D11.500 lateral surface length = 2.000 mm
- cylindrical D10.800 lateral surface length = 6.000 mm

Therefore the P006 Ø11.5 head occupies the exact x=0...+2 mm region that
Gate03B-v4 incorrectly narrowed to ID10.917.

## v5 principle

Do not invent a new P007 front cavity.

Take the current production P007 and remove only its first 5.000 mm sleeve.

This preserves:
- ID14.1 around P006 head from x=0...+2
- thin ID start x=+2
- thin OD start x=+3
- rear inner x=+34
- rear outer x=+35

The removed old sleeve occupied x=-5...0 with OD16 around P003 OD14.
Transfer that envelope to P003 as a rear OD16 collar, length 5 mm.

Gate03E does NOT modify production P003. It creates a separate OD16/ID14/L5
collar reference body for the next assembly geometry gate.

## Run

1. New unsaved Part:
   `RUN_1_K01_GATE03E_BUILD_P007_V5.cmd`

2. New unsaved Part:
   `RUN_2_K01_GATE03E_BUILD_P003_COLLAR_REF.cmd`

Send both JSON reports.

Gate03F will insert the P007-v5 candidate plus the collar-reference into a copy
of the real assembly and rerun the P006/P007 and full assembly interference gate.

Static/Buckling remain blocked until Gate03F PASS.
