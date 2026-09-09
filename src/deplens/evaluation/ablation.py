from __future__ import annotations

from dataclasses import dataclass

from deplens.evaluation.metrics import BinaryMetrics
from deplens.evaluation.scoring import score_rules
from deplens.prediction.baselines import UpdateCase

METADATA_RULES = ("major-version", "direct-dependency", "api-change", "dependency-depth")
USAGE_RULES = ("code-usage",)


@dataclass(frozen=True)
class AblationResult:
    metadata_best_rule: str
    metadata_f1: float
    usage_best_rule: str
    usage_f1: float
    delta_f1: float
    delta_precision: float
    delta_recall: float
    scores: dict[str, BinaryMetrics]


def _best(scores: dict[str, BinaryMetrics], rules: list[str]) -> tuple[str, BinaryMetrics]:
    return max(((rule, scores[rule]) for rule in rules), key=lambda item: item[1].f1)


def ablate(
    cases: list[UpdateCase],
    labels: list[bool],
    metadata_rules: tuple[str, ...] = METADATA_RULES,
    usage_rules: tuple[str, ...] = USAGE_RULES,
) -> AblationResult:
    scores = score_rules(cases, labels)
    for rule in (*metadata_rules, *usage_rules):
        if rule not in scores:
            raise ValueError(f"unknown rule: {rule}")
    metadata_rule, metadata_metrics = _best(scores, list(metadata_rules))
    usage_rule, usage_metrics = _best(scores, list(usage_rules))
    return AblationResult(
        metadata_best_rule=metadata_rule,
        metadata_f1=metadata_metrics.f1,
        usage_best_rule=usage_rule,
        usage_f1=usage_metrics.f1,
        delta_f1=usage_metrics.f1 - metadata_metrics.f1,
        delta_precision=usage_metrics.precision - metadata_metrics.precision,
        delta_recall=usage_metrics.recall - metadata_metrics.recall,
        scores=scores,
    )
