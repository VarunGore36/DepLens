from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BinaryMetrics:
    tp: int
    tn: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    false_negative_rate: float
    accuracy: float
    support: int


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def compute_binary_metrics(y_true: list[bool], y_pred: list[bool]) -> BinaryMetrics:
    if len(y_true) != len(y_pred):
        raise ValueError(f"length mismatch: {len(y_true)} true vs {len(y_pred)} predicted")
    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    tn = sum(1 for t, p in zip(y_true, y_pred) if not t and not p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    return BinaryMetrics(
        tp=tp,
        tn=tn,
        fp=fp,
        fn=fn,
        precision=precision,
        recall=recall,
        f1=_safe_div(2 * precision * recall, precision + recall),
        false_positive_rate=_safe_div(fp, fp + tn),
        false_negative_rate=_safe_div(fn, fn + tp),
        accuracy=_safe_div(tp + tn, len(y_true)),
        support=len(y_true),
    )


def brier_score(y_true: list[bool], y_prob: list[float]) -> float:
    if len(y_true) != len(y_prob):
        raise ValueError(f"length mismatch: {len(y_true)} true vs {len(y_prob)} predicted")
    if not y_true:
        return 0.0
    return sum((p - (1.0 if t else 0.0)) ** 2 for t, p in zip(y_true, y_prob)) / len(y_true)


def roc_auc(y_true: list[bool], y_score: list[float]) -> float:
    if len(y_true) != len(y_score):
        raise ValueError(f"length mismatch: {len(y_true)} true vs {len(y_score)} scored")
    positives = sum(1 for t in y_true if t)
    negatives = len(y_true) - positives
    if positives == 0 or negatives == 0:
        return 0.0
    ranked = sorted(range(len(y_true)), key=lambda i: (y_score[i], i))
    rank_sum = 0.0
    for position, i in enumerate(ranked, start=1):
        if y_true[i]:
            rank_sum += position
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)
