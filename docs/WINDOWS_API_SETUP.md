# Windows API setup — exact sequence

The Microsoft Store Python alias may point to a missing `WindowsApps\python.exe`.
For K01 CAD automation, prefer the Python Launcher (`py`) or an official python.org CPython 3.12 x64 installation.

From the repository root:

```bat
where python
where py
py -0p
py -3.12 --version
```

If `py -3.12 --version` works:

```bat
py -3.12 -m pip install --user pywin32
RUN_SW_API_PROBE.cmd
```

Before running the probe:
- start SOLIDWORKS 2026;
- open the native K01-P-016 part;
- save it once;
- keep SOLIDWORKS running.

Expected output:
`reports\CAD_SNAPSHOT_probe.json`

The first probe is read-only. It must not modify production geometry.
