# Research Questions

Status: `in progress` (Phase 0). Questions are fixed for initial milestones; refinements require issue + docs update.

## Central Question

> Can dependency graphs, code usage information, API relationships, and historical evidence be used to predict the impact of dependency updates before they are applied?

Constraint: only information available **before** the update may be used as features.

## RQ1 — Affected-code identification

How accurately can dependency and code-usage information identify code that may be affected by a dependency update?

- Input: repo snapshot at parent commit + proposed version bump.
- Output: set of files / modules / functions predicted affected.
- Evaluated against actually changed/failing code post-update (Phase 3 labels).

## RQ2 — Predictive signals

Which signals are most predictive of actual downstream breakage?

Candidate signals (all unevaluated):

- dependency depth
- direct vs transitive dependency
- version distance
- semantic-version change
- removed/changed APIs
- number of affected imports
- affected functions/classes
- dependency centrality
- test coverage
- historical breakage frequency
- maintainer/release activity
- number of downstream dependents

Method: univariate analysis + ablation + feature importance from Phase 4–6 models.

## RQ3 — Pre-update predictability

Can historical dependency-update failures be predicted before the update occurs?

Requires dated dataset, temporal splits, no leakage. Success criterion defined in `methodology.md` (precision/recall targets set per experiment, no global claim in advance).

## RQ4 — Value of usage information

Does combining dependency metadata with source-code usage provide substantially better predictions than dependency metadata alone?

Tested by ablation: metadata-only baseline vs. metadata + usage. Report delta in precision/recall/F1.

## RQ5 — ML / LLM value-add

Can ML or LLM-based approaches improve upon deterministic/static-analysis baselines?

LLM-assisted API impact analysis is `experimental`. Must beat Phase 4 baselines on the same splits to be retained.
