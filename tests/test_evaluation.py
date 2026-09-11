import pytest

from deplens.evaluation import (
    brier_score,
    compute_binary_metrics,
    results_table,
    roc_auc,
    score_rules,
)
from deplens.prediction import UpdateCase


def test_perfect_predictions():
    m = compute_binary_metrics([True, True, False], [True, True, False])
    assert (m.tp, m.tn, m.fp, m.fn) == (2, 1, 0, 0)
    assert m.precision == 1.0 and m.recall == 1.0 and m.f1 == 1.0
    assert m.false_positive_rate == 0.0 and m.false_negative_rate == 0.0
    assert m.accuracy == 1.0 and m.support == 3


def test_mixed_predictions():
    m = compute_binary_metrics([True, True, False, False], [True, False, True, False])
    assert (m.tp, m.tn, m.fp, m.fn) == (1, 1, 1, 1)
    assert m.precision == 0.5 and m.recall == 0.5 and m.f1 == 0.5
    assert m.false_positive_rate == 0.5 and m.false_negative_rate == 0.5


def test_zero_division_safe():
    m = compute_binary_metrics([False, False], [False, False])
    assert m.precision == 0.0 and m.recall == 0.0 and m.f1 == 0.0
    assert m.accuracy == 1.0


def test_length_mismatch_raises():
    with pytest.raises(ValueError, match="length mismatch"):
        compute_binary_metrics([True], [True, False])


def test_brier_score():
    assert brier_score([True, False], [1.0, 0.0]) == 0.0
    assert brier_score([True, False], [0.5, 0.5]) == 0.25
    assert brier_score([], []) == 0.0
    with pytest.raises(ValueError, match="length mismatch"):
        brier_score([True], [])


def test_roc_auc():
    assert roc_auc([True, True, False, False], [0.9, 0.8, 0.2, 0.1]) == 1.0
    assert roc_auc([True, False], [0.0, 1.0]) == 0.0
    assert roc_auc([True, True], [0.5, 0.5]) == 0.0
    assert roc_auc([], []) == 0.0
    with pytest.raises(ValueError, match="length mismatch"):
        roc_auc([True], [])


def test_results_table():
    cases = [UpdateCase("a", "1.0.0", "2.0.0", direct=True, depth=1)]
    scores = score_rules(cases, [True])
    plain = results_table(scores)
    assert "| major-version | 1.00 | 1.00 | 1.00 |" in plain
    assert "ROC-AUC" not in plain
    probs = {rule: [1.0 if rule == "major-version" else 0.0] for rule in scores}
    full = results_table(scores, probs, [True])
    assert "ROC-AUC" in full and "Brier" in full
