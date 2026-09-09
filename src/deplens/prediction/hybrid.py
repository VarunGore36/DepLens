from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from deplens.prediction.baselines import Prediction, UpdateCase, semver_change

SIGNAL_NAMES = ("major", "direct", "deep", "api", "usage")


@dataclass(frozen=True)
class HybridWeights:
    major: float = 1.0
    direct: float = 0.0
    deep: float = 0.0
    api: float = 0.0
    usage: float = 0.0
    threshold: float = 0.5

    def as_dict(self) -> dict[str, float]:
        return {
            "major": self.major,
            "direct": self.direct,
            "deep": self.deep,
            "api": self.api,
            "usage": self.usage,
            "threshold": self.threshold,
        }


def signals(case: UpdateCase) -> dict[str, float]:
    return {
        "major": 1.0 if semver_change(case.old_version, case.new_version) == "major" else 0.0,
        "direct": 1.0 if case.direct else 0.0,
        "deep": 1.0 if case.depth is None or case.depth >= 2 else 0.0,
        "api": 1.0 if case.api_changed is True else 0.0,
        "usage": 1.0 if case.affected_imports > 0 or case.affected_apis > 0 else 0.0,
    }


def hybrid_score(case: UpdateCase, weights: HybridWeights) -> float:
    values = signals(case)
    total = sum(getattr(weights, name) for name in SIGNAL_NAMES)
    if total <= 0:
        return 0.0
    earned = sum(getattr(weights, name) * values[name] for name in SIGNAL_NAMES)
    return earned / total


def hybrid_predict(case: UpdateCase, weights: HybridWeights) -> Prediction:
    score = hybrid_score(case, weights)
    return Prediction(package=case.package, rule="hybrid", score=score, label=score >= weights.threshold)


def _f1(y_true: list[bool], y_pred: list[bool]) -> float:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
    if tp == 0:
        return 0.0
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    return 2 * precision * recall / (precision + recall)


def fit_grid(
    cases: list[UpdateCase],
    labels: list[bool],
    grid: tuple[float, ...] = (0.0, 0.5, 1.0),
) -> HybridWeights:
    best = HybridWeights()
    best_f1 = _f1(labels, [hybrid_predict(case, best).label for case in cases])
    for values in product(grid, repeat=len(SIGNAL_NAMES)):
        candidate = HybridWeights(*values)
        f1 = _f1(labels, [hybrid_predict(case, candidate).label for case in cases])
        if f1 > best_f1:
            best, best_f1 = candidate, f1
    return best
