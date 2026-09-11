from __future__ import annotations

from deplens.evaluation.metrics import BinaryMetrics, brier_score, roc_auc


def results_table(
    scores: dict[str, BinaryMetrics],
    probs: dict[str, list[float]] | None = None,
    labels: list[bool] | None = None,
) -> str:
    use_auc = probs is not None and labels is not None
    header = "| Rule | Precision | Recall | F1 | FP rate | FN rate"
    divider = "| --- | --- | --- | --- | --- | ---"
    if use_auc:
        header += " | ROC-AUC | Brier |"
        divider += " | --- | --- |"
    lines = [header, divider]
    for rule in sorted(scores):
        m = scores[rule]
        row = f"| {rule} | {m.precision:.2f} | {m.recall:.2f} | {m.f1:.2f} | {m.false_positive_rate:.2f} | {m.false_negative_rate:.2f}"
        if use_auc:
            assert probs is not None and labels is not None
            row += f" | {roc_auc(labels, probs[rule]):.2f} | {brier_score(labels, probs[rule]):.2f} |"
        lines.append(row)
    return "\n".join(lines)
