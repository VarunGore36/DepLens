# Methodology

Status: `in progress` (Phase 0 draft). This is the normative protocol for all DepLens experiments.

## 1. Pipeline

Repository → Dependency extraction → Dependency graph → Source-code/import analysis → API/usage analysis → Dependency update detection → Potential impact estimation → Historical failure dataset → Prediction → Evaluation

## 2. Principles

1. **Pre-update features only.** Features must be computable at the parent commit. Any use of post-update information (changelog after release, failure logs) as input invalidates a run.
2. **Baselines first.** No ML/LLM result is reported without comparison to Phase 4 deterministic baselines on identical splits.
3. **Temporal splits.** Train on older updates, test on newer updates. No random splits that leak future breakage patterns.
4. **Negative results are published.** Non-predictive signals are documented in `experiments/results/`.
5. **Reproducibility.** Every experiment records: commit SHA, dataset version, seed, environment (Python version, `pip freeze` / lockfile), and exact command.

## 3. Data Collection (Phase 3)

- Sample Python repositories with Git history and CI.
- Detect update commits: Dependabot/Renovate PRs, `requirements.txt` / `pyproject.toml` / lockfile diffs.
- Label outcomes via CI status, test results, revert/fix commits.
- Store: repo, parent SHA, update SHA, dependency, version delta, label, label provenance.
- Document license/provenance per entry in `datasets/README.md`.

## 4. Feature Families

- Metadata: depth, direct/transitive, version distance, semver type, centrality, release activity.
- Usage: affected imports count, affected functions/classes, coverage of affected code.
- Historical: prior breakage frequency of dependency, downstream dependent count.

All features versioned in `src/deplens/` with unit tests.

## 5. Evaluation

Metrics: precision, recall, F1, false-positive rate, false-negative rate, calibration (Brier score / reliability where probabilistic).

Report sliced by: direct vs transitive, major vs minor/patch, with/without API change.

## 6. Experiment Tracking

- Definitions: `experiments/baselines/` (and later `experiments/<method>/`).
- Outputs: `experiments/results/<date>-<experiment>/` with `README.md`, `metrics.json`, `config.yaml`.
- Never overwrite; new run = new directory.
