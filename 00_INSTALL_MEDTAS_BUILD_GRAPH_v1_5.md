# Install MEDTAS v1.5

Copy/expand all archive contents into:

`D:\BreshevEngineering\marvilon-k01\`

with overwrite enabled.

Then run:

`03_RUN_MEDTAS_PIPELINE.cmd`

The working Control Center is:

`OPEN_K01_COMMAND_CENTER_V10.cmd`

Do **not** use `reports\control\K01_MEDTAS_CENTER_CURRENT.html` as the primary UI; it is only a generated diagnostic snapshot.

The first successful CAD semantic run must later be qualified using:

`06_TEST_CAD_HASH_INVARIANCE.cmd`

A failed CAD export produces `BLOCKED_EXPORT`, not a false canonicalization failure.
