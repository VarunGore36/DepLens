# `evaluation` — Status: `in progress` (Phase 5)

`metrics.py` provides binary classification metrics (precision, recall, F1, FP/FN rates, accuracy) and Brier score for calibration. `scoring.py` scores every baseline rule against one labeled case list for head-to-head comparison. `ablation.py` compares metadata-only rules against usage-aware rules for RQ4 (best-F1 per group plus precision/recall deltas). `splits.py` gives date-ordered train/test index splits against future leakage; `strata.py` scores per stratum (direct/transitive, major/non-major, or any caller grouping).
