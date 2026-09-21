# K01 Center integration plan

## Evidence boundary
This review is based on the delivered K01_CENTER_LIVE code and the visible conversation. The shared conversation at https://chatgpt.com/share/6aa1b98d-3c7c-83ed-9d18-f91086b73bc1 could not be retrieved. No current CAD QA outcome is inferred from its existence. The live repository and latest handoff are required to bind new routes and acceptance rules.

## What exists
The Center reads explicitly configured reports, displays P007/D006 evidence and BOM, exposes three declared dispatcher commands, observes saved-file metadata, and can invoke the existing handoff builder. File events do not constitute a CAD snapshot, a dependency calculation, an engineering verdict or a backup. The event history resets on server restart. Git metadata is not evidence of a successful remote backup.

## Priority 1: one current engineering work item
Have the project engine publish an explicit current work item: ID, objective, baseline assembly path/configuration/physical hash, candidate paths/hashes, input requirements, last run ID, failure reasons, required evidence, and next command ID. Preserve completed decisions and rejected alternatives. For ongoing assembly QA, bind the exact current report rather than infer success from a console return code or an older PASS. Acceptance: the Center identifies which assembly/report it describes and offers one valid next action with prerequisites.

## Priority 2: saved change -> affected verification
Keep the file observer separate from the dependency engine. The engine maps declared input paths and hashes to affected nodes, propagates stale status through declared dependencies and publishes a rerun plan. Unmapped changes are visible as UNMAPPED, not silently ignored or assigned to guessed nodes. Changes in an export, copied file, timestamp or directory name do not prove a semantic geometry change. Acceptance: a controlled fixture changes one input and yields the expected dependent checks while unaffected checks remain reusable.

## Priority 3: run -> evidence -> actionable failure
Dispatcher capabilities must declare stable command IDs, prerequisites and output contracts. The Center launches only declared commands. Record input fingerprints, start/end times, tool version, output paths, return code and engineering result separately. Stream logs, support reliable child-process cancellation and keep persistent run history. Current launcher timeout is not complete child-process supervision. For CAD actions use the existing backend and candidate rules, not a second CAD implementation inside the Center. Acceptance: a failure links the exact report and preserves the prior valid candidate; a successful process without required output is never accepted.

## Priority 4: requirements and module closure
Inventory the actual repository first. Reconcile active requirement IDs, sources, approval and verification states without replacing originals silently. Resolve quantitative leak acceptance and actuator load provenance through controlled engineering decisions. Product-definition work items must carry next_action and expected_evidence by exact ID. For every manufactured part, expose material, drawing revision, tolerance/inspection coverage and evidence. Keep EBOM-to-MBOM transformations explicit. Acceptance: each release blocker has a source, responsible work item and closure evidence; unresolved numbers remain OPEN.

## Priority 5: handoff and recovery
Build handoff from the same run/input identity shown by the Center; include a readable resume note, active blockers, run manifest, requirements inventory and source paths. Show file count/hash/time after completion. Persist activity/run history and checkpoint manifests outside project root clutter. Separate source-controlled code/definitions from heavy CAD and generated artifacts. Verify remote Git/LFS or chosen CAD backup by restoration, not by local commit existence. Do not auto-push or auto-promote CAD on filesystem events.

## Daily use
Open the current task; inspect the exact candidate/report; change the controlled source; save; capture the needed backend snapshot; follow the engine's affected-check plan; inspect the output and engineering reasons; generate a handoff at a work checkpoint. The Center should remove repeated searching and manual command selection.

## Scope control
Finish the calibration module with this minimal evidence-to-action workflow before a broad FreeCAD migration or independent shell rewrite. Keep CAD access in backends, verdict/dependency logic in the engine and presentation in the Center. Introduce contracts where current work needs them; do not rebuild functioning tooling only to rename it.

## Next implementation input
Use Build AI handoff and provide the resulting archive together with the shared-chat export if its decisions are not captured in the handoff. This allows exact mapping of the current Gate04B/assembly QA producer and command contract without inventing paths or repeating completed work.
