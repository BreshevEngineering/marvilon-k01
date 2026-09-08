# K01 Continue 06

Extract directly into:

`D:\BreshevEngineering\marvilon-k01\`

Run only:

`06_RUN_K01_CONTINUE.cmd`

## Exact cause of the last failure

PowerShell has a built-in alias:

`r -> Invoke-History`

Closure 05 defined a function named `R` and then called:

`R "REQ-K01-MAT-P006-001"`

PowerShell command precedence selected the built-in alias instead of the intended helper function, therefore it tried to find that text in command history.

Continue 06 removes every single-letter helper name.

The controlled helper is now:

`Get-K01Requirement`

## No more Gate04E rerun

The previous run already produced corrected Gate04E v3 PASS evidence and a full verification assembly. Continue 06 validates that evidence and proceeds from it. It does not rebuild CAD again.

## Sequence

1. Close T03 + pressure + accepted CFD temperature.
2. Run T05 compact-flange analytical screen.
3. Run read-only P006 drawing probe.
4. Build FEMM screening input pack.
5. Build AI handoff ZIP.
6. Build module-closure status.

Only step 1 is a hard stop. Later evidence-collection steps report HOLD but do not prevent the rest of the chain from running.
