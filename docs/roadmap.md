# Roadmap

Status legend: `implemented` / `in progress` / `planned` / `experimental` / `hypothetical`.

## Phase 0 — Project setup (`in progress`)

- [x] Repository structure
- [x] Research questions, methodology, roadmap docs
- [ ] Contribution guide, code of conduct
- [x] Experiment tracking convention, repo CI (pytest + ruff)

## Phase 1 — Dependency graph (`in progress`)

- [x] Parse `requirements.txt`, `pyproject.toml`, lockfiles (poetry/uv/Pipfile)
- [x] Construct direct/transitive graph, version constraints
- [x] Graph features: depth, dependents, fan-in/fan-out, degree centrality
- [ ] Live transitive resolution via package metadata
- Module: `src/deplens/dependencies/`, `src/deplens/graph/`

## Phase 2 — Code usage analysis (`in progress`)

- [x] Parse Python source (AST), identify imports
- [x] Map imports → dependencies (stdlib filter, alias table)
- [x] Qualified API-usage tracking with per-dependency filtering
- [ ] Scope/shadowing precision, relative and star imports
- Module: `src/deplens/analysis/`

## Phase 3 — Dependency update dataset (`in progress`)

- [x] Identify historical updates from git history (deduplicated, marker/extras-sensitive diff)
- [x] Heuristic labels (reverts, fix-commits)
- [x] Worktree test-outcome labeling (`breaks-tests` / `passes` / `already-failing` / `no-tests`)
- [x] Isolated per-commit venvs with era installs incl. test extras (`label_test_outcomes_isolated`)
- [ ] Curated real-data dataset in `datasets/`
- Module: `src/deplens/updates/` + `datasets/`

## Phase 4 — Baselines (`in progress`)

- [x] Major-version, direct-dependency, API-change, depth, code-usage heuristics
- [x] Measured `UpdateCase` builder from graph + usage
- Module: `src/deplens/prediction/`, definitions in `experiments/baselines/`

## Phase 5 — Evaluation (`in progress`)

- [x] Precision, recall, F1, FP/FN rates, calibration (Brier), per-rule scoring, metadata-vs-usage ablation
- [x] Temporal splits, per-stratum reporting
- [ ] Published results on real labeled data
- Module: `src/deplens/evaluation/`

## Phase 6 — Advanced methods (`in progress`, unevaluated)

- [x] Graph features, grid-fit hybrid model, LLM-adapter seam (`ApiDiffProvider`)
- [ ] Classical ML on real data, code embeddings, evaluated LLM backend
- All Phase 6 outputs are unevaluated until run against a real labeled dataset.

## Phase 7 — Developer tool (`in progress`, conditional)

- [x] CLI (`deplens analyze|predict|updates`), JSON/markdown reports, risk scoring, GitHub workflow + PR comments
- [ ] Validation that scores are useful before recommending adoption
- Tooling exists for research use; usefulness is not yet demonstrated.
