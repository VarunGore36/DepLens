# `updates` — Status: `in progress` (Phase 3)

`detection.py` mines dependency bumps from git history by diffing parsed dependency files per commit (`UpdateRecord` with old/new constraints, added/removed/updated). `labeling.py` assigns heuristic ground-truth labels (`reverted` / `fix-suspect` / `no-signal`) from later revert and fix commits. `test_outcomes.py` runs a caller-supplied test command in isolated worktrees at parent and update commits, labeling `breaks-tests` / `passes` / `already-failing` / `error` / `timeout` — no dependency installation, so old trees must already be runnable.
