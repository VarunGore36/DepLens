from __future__ import annotations

from deplens.evaluation.metrics import BinaryMetrics, compute_binary_metrics
from deplens.prediction.baselines import BASELINES, UpdateCase


def score_rules(cases: list[UpdateCase], labels: list[bool]) -> dict[str, BinaryMetrics]:
    if len(cases) != len(labels):
        raise ValueError(f"length mismatch: {len(cases)} cases vs {len(labels)} labels")
    return {
        rule: compute_binary_metrics(labels, [fn(case).label for case in cases])
        for rule, fn in BASELINES.items()
    }
