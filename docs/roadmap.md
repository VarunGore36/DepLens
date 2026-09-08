# Roadmap

Status legend: `implemented` / `in progress` / `planned` / `experimental` / `hypothetical`.

## Phase 0 — Project setup (`in progress`)

- [x] Repository structure
- [x] Research questions, methodology, roadmap docs
- [ ] Contribution guide, code of conduct
- [ ] Experiment tracking convention, CI scaffold

## Phase 1 — Dependency graph (`planned`)

- Parse `requirements.txt`, `pyproject.toml`, lockfiles where practical
- Construct direct/transitive graph
- Represent version constraints, support package metadata
- Module: `src/deplens/dependencies/`, `src/deplens/graph/`

## Phase 2 — Code usage analysis (`planned`)

- Parse Python source (AST), identify imports
- Map imports → dependencies
- Investigate function/class/API-level relationships
- Module: `src/deplens/analysis/`

## Phase 3 — Dependency update dataset (`planned`)

- Identify historical updates, collect repos/commits
- Determine failures, establish ground-truth labels
- Module: `src/deplens/updates/` + `datasets/`

## Phase 4 — Baselines (`planned`)

- Major-version heuristic, direct-dependency heuristic, API-change heuristic, depth heuristic
- Module: `src/deplens/prediction/`, definitions in `experiments/baselines/`

## Phase 5 — Evaluation (`planned`)

- Precision, recall, F1, FP/FN rates, calibration
- Module: `src/deplens/evaluation/`

## Phase 6 — Advanced methods (`experimental / planned`)

- Graph features, classical ML, code embeddings, LLM-assisted API analysis, hybrids

## Phase 7 — Developer tool (`hypothetical`)

- Only if research justifies it: CLI, reports, GitHub Action, PR comments, risk scoring
