# K01 repository control patch v01

Why `master/` was missing:
Git does not track empty directories. The starter created a `master` folder, but
until it contained a file it could not appear in the repository.

Copy this patch into the repository root.

Expected new files:
- `master/K01_master.json`
- `params/k01_params.py`
- `tests/test_k01_master.py`
- `docs/K01_CURRENT_GATES.md`

Then run:
```bat
cd /d D:\BreshevEngineering\marvilon-k01
py -3.12 -m pytest -q
git add .
git status
git commit -m "feat: add K01 master control and interface gates"
git push
```

The existing `params/k01_params_example.py` can be deleted after the new tests pass.
