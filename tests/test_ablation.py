import pytest

from deplens.evaluation import ablate
from deplens.prediction import UpdateCase


def test_ablate_usage_beats_metadata():
    cases = [
        UpdateCase("a", "1.0.0", "1.0.1", direct=False, depth=3, affected_imports=2),
        UpdateCase("b", "1.0.0", "1.0.1", direct=False, depth=3, affected_imports=0),
    ]
    result = ablate(cases, [True, False])
    assert result.usage_best_rule == "code-usage"
    assert result.usage_f1 == 1.0
    assert result.delta_f1 > 0


def test_ablate_metadata_beats_usage():
    cases = [
        UpdateCase("a", "1.0.0", "2.0.0", direct=True, depth=1, affected_imports=0),
        UpdateCase("b", "1.0.0", "1.0.1", direct=False, depth=3, affected_imports=0),
    ]
    result = ablate(cases, [True, False])
    assert result.metadata_f1 == 1.0
    assert result.delta_f1 < 0


def test_ablate_unknown_rule_raises():
    with pytest.raises(ValueError, match="unknown rule"):
        ablate([UpdateCase("a")], [True], metadata_rules=("nope",))
