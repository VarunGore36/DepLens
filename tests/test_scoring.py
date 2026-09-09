import pytest

from deplens.evaluation import score_rules
from deplens.prediction import UpdateCase


def test_score_rules_perfect_major_signal():
    cases = [
        UpdateCase("a", "1.0.0", "2.0.0", direct=True, depth=1),
        UpdateCase("b", "1.0.0", "1.1.0", direct=False, depth=2),
    ]
    scores = score_rules(cases, [True, False])
    assert scores["major-version"].accuracy == 1.0
    assert scores["direct-dependency"].accuracy == 1.0
    assert scores["dependency-depth"].accuracy == 0.0
    assert set(scores) == {"major-version", "direct-dependency", "api-change", "dependency-depth"}


def test_score_rules_length_mismatch():
    with pytest.raises(ValueError, match="length mismatch"):
        score_rules([UpdateCase("a")], [True, False])
