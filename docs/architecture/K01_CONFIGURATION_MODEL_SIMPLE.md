# K01 configuration model — simple baseline

The enforced configuration model is intentionally small:

1. **Authority** = Git commit + immutable evidence + external CAD manifest.
2. **State** = derived from clean Git HEAD + CAD manifest; a dirty controlled worktree is not a valid state.
3. **Change** = branch == `change_id` + one transaction JSON + exact scope; added files are declared individually.
4. **Control** = trusted PR gate executed from the base branch + K01 tests.
5. **Close** = merge to protected `main` + clean main + checkpoint tag.
6. **Center** = read-only projection; stale HEAD can never be PASS.

`reports/**` is runtime output and never engineering authority. If a report becomes decision/release evidence, it is promoted by content hash to `evidence/immutable/**` before the report tree is removed from Git tracking.
