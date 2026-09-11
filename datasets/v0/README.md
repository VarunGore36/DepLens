# DepLens v0 dataset

42 cases. Every row is a real dependency update with pre-update features and a label.
Schema per JSON line:

`dataset, repo_url, commit, package, change, old_constraint, new_constraint,
old_version, new_version, direct, depth, affected_imports, affected_apis,
label_kind, label, evidence[, provenance]`

## Groups

- **40 weak-label cases** (`label_kind: weak`): most recent updates from
  `psf/requests` and `encode/httpx`, features reconstructed at each parent commit
  via `git archive` (`scripts/first_experiment.py`). Labels map heuristic outcomes
  (`reverted`/`fix-suspect` → true, `no-signal` → false). The `/tmp` checkout paths
  in the original run are replaced here by canonical repo URLs; commit SHAs are intact.
- **2 test-grounded cases** (`label_kind: test`): suites executed in isolated
  worktrees at parent and update commits, both passing (`label: false`).
  `tomli` addition from DepLens's own history (repo predates publication, no URL);
  `cryptography` 47→49 `uv.lock` update in `urllib3`
  (`13fa1e03`, full closure via `uv sync --locked`).

## Known limits

- Weak labels are proxies, not confirmed breakage; `no-signal` especially understates failures.
- `old_version`/`new_version` are null for range constraints and multi-entry lock joins
  (e.g. the `cryptography` row: `==2.3|==47.0.0` spans resolution markers); those cases
  cannot exercise the semver rule by construction.
- No commit dates are stored, so this snapshot cannot drive temporal splits yet.
- n=42 with 1 weak positive and 0 test positives: useful for pipeline validation and
  regression-testing the harness, not for claims about predictive power.
