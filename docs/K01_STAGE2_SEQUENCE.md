# K01 stage-2 sequence — do not branch

1. Open stable K01-A-001 after P003/P007 promotion and run post-promotion QA.
2. If PASS, close SOLIDWORKS and run candidates cleanup dry-run → apply.
3. Run repo cleanup dry-run → apply; inspect `git status`, do not commit yet.
4. Run Gate04B Datum C candidate builder.
5. Send Gate04B console + JSON; perform one assembly QA of P003/P016/P017 concept.
6. Freeze P014/P015/material metadata.
7. Run CFD OUT/MID/IN only.
8. Close actuator budget.
9. Generate/update final drawings, master, BOM.
10. Commit/push and tag design freeze.
11. Move the frozen module into the SW2026 laptop/project.
