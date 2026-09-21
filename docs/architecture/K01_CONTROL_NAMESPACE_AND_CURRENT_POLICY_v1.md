# K01 control namespace and CURRENT policy — v1

## Problem being controlled

Historical version files are currently present in `control/` and some generated report families. Filename recency or lexicographic order must never decide engineering authority.

## Rule

1. Critical logical families have one exact authority path declared in `control/project/K01_AUTHORITY_MAP_CURRENT.json::control_families`.
2. Existing version siblings are migration debt/history. They are not fallback authority.
3. `control/repo/K01_CONTROL_NAMESPACE_BASELINE.json` freezes current family membership: history may shrink, but adding `vNext` beside a live family is blocked until a reviewed migration updates the baseline/authority.
4. Stable unversioned names are the target architecture. Migration is done per family after active Baseline-02C promotion, not as a mass rename during a CAD authority transaction.
5. `CURRENT` means current pointer/projection. It must not be combined with version proliferation. JSON+CSV representations of one current entity are allowed; same-format versioned CURRENT siblings are not a selection mechanism.
6. Tools touched going forward must resolve critical authorities from the authority map, not `sorted(glob)[-1]` or fallback chains.

This is a stop-the-bleeding migration guard. It makes the current authority unambiguous immediately without deleting history during the active promotion transaction.

## Local/transient files

Patch inboxes and installer packages are not repository roots. `_inbox` must be relocated outside the repository (default local target `%LOCALAPPDATA%\Marvilon\K01\inbox`). Legacy Center-panel installer package files at root are preserved by hash and quarantined under `reports/migration/quarantine/`, never silently deleted.

## Workstation vs handoff inventory

The namespace baseline is a **reviewed control artifact**, not a raw derivative of the AI handoff archive. A handoff may omit non-source binary/UI history. Therefore:

- live `repo_guard`/namespace inventory is authoritative for detecting what physically exists in the working repository;
- if a live family is absent from the reviewed baseline, the guard must HOLD;
- there is no automatic `accept current tree` or `bootstrap all` command;
- after review, an exact legacy family may be adjudicated into shrink-only migration debt;
- adjudicating legacy presence does not make it engineering authority.

The 2026-09-10 Baseline-02C hardening exposed this case for the legacy Engineering Control Center workbooks and Command Center HTML versions. They are explicitly NON-AUTHORITY and frozen as migration debt until a later controlled UI/history cleanup.

## Patch transport after root cleanup

After `_inbox` is relocated, patch transport is outside the Git worktree by default: `%LOCALAPPDATA%\Marvilon\K01\inbox`. Do not recreate a repository-root `_inbox` merely to apply a later patch.


## Archive hygiene update — 2026-09-14
Confirmed superseded/history sources are physically relocated under `archive/` by the controlled archive migration tool. `archive/` is ignored by Git/default AI handoff and cannot compete with active authority. Versioned live-family cleanup remains a separate reviewed namespace migration because active executors may still reference those files.
