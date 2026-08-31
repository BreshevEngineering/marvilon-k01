# GitHub setup checklist — BreshevEngineering

Recommended ownership model:
- personal GitHub account(s) for real people;
- GitHub Organization: `BreshevEngineering`;
- corporate email verified on the owner account;
- private repository: `k01-calibration-module-engineering`.

Security:
- enable passkey/security key or authenticator-based 2FA;
- save recovery codes offline;
- do not create a shared company login;
- keep repository private;
- do not store access tokens in the repository.

Repository:
- default branch: `main`;
- enable Issues;
- disable Wiki unless it is intentionally used;
- do not add an open-source license to proprietary IP;
- add a proprietary notice if required by the company.

First commits:
1. `chore: initialize K01 engineering control`
2. `feat: add P003-P016 locating interface baseline`
3. later: `feat: add SolidWorks API CAD snapshot`

When plan/features allow:
- protect `main`;
- prohibit force-push/delete;
- require QA status checks;
- require pull request for controlled/release changes.
