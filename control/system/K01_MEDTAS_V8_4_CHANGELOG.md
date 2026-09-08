# MEDTAS v8.4 changelog

## Reliability correction

Root cause of the reported `/api/git` HTTP 500:

The v8.3 server accidentally contained this semantic shape inside `GitState`:

`classification = J <path1>,<path2>,<path3>...`

PowerShell therefore passed an `Object[]` as the `ChildPath` argument of `Join-Path`, producing:

`Cannot convert 'System.Object[]' to the type 'System.String' required by parameter 'ChildPath'.`

v8.4 removes the compressed GitState implementation entirely.

## Architecture changes

- Added shared `cc_api_core_v8.ps1`.
- Git classification and GitHub remote-health are loaded as separate single-path artifacts.
- Added read-only `RUN_K01_COMMAND_CENTER_SELFTEST`.
- Control Center launcher runs the self-test before starting the server.
- Browser refresh uses `Promise.allSettled`; State/Git/Files fail independently.
- Added subsystem-health card.
- Structured endpoint errors include the failing endpoint.
- Added MEDTAS reliability standard and platform-freeze rule.

## Engineering priority

No new nonessential MEDTAS features until:
1. Gate04E P006 build + full-assembly verification succeeds.
2. T04 seal/media inputs are materially advanced.
3. T05 clamp/local-contact release evidence is materially advanced.

This keeps infrastructure subordinate to K01 engineering.
