# Install MEDTAS v1.4

1. Close any old MEDTAS v9 proxy console if it is running.
2. Extract this overlay into `D:\BreshevEngineering\marvilon-k01\` and replace files.
3. Keep SOLIDWORKS running.
4. Run `03_RUN_MEDTAS_PIPELINE.cmd`.
5. If CAD semantic extraction passes, run `06_TEST_CAD_HASH_INVARIANCE.cmd` and perform the requested two no-change saves.
6. Start the main UI with `OPEN_K01_COMMAND_CENTER_V9.cmd`.

The previous static `reports\control\K01_MEDTAS_CENTER_CURRENT.html` is a diagnostic materialized view, not the main user interface.
