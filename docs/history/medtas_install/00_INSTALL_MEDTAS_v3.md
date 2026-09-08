# INSTALL K01 MEDTAS v3

Extract this archive directly into:

`D:\BreshevEngineering\marvilon-k01\`

Do not create a nested MEDTAS project folder.

Then run:

`control\command_center\OPEN_K01_COMMAND_CENTER_V3.cmd`

v3 no longer depends on Python. The local navigation/status server is implemented
in Windows PowerShell/.NET and listens only on 127.0.0.1:8765.

This package does not modify stable CAD, candidate CAD, current master JSON or Git history.
