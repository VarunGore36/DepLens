import pytest

from deplens.evaluation import (
    directness_stratum,
    score_by_stratum,
    semver_stratum,
    temporal_split,
)
from deplens.prediction import UpdateCase


def test_temporal_split_orders_by_date():
    train, test = temporal_split(["2024-03-01", "2024-01-01", "2024-02-01"], 0.67)
    assert train == [1, 2]
    assert test == [0]


def test_temporal_split_rejects_bad_fraction():
    with pytest.raises(ValueError, match="train_fraction"):
        temporal_split(["2024-01-01", "2024-02-01"], 1.0)
    with pytest.raises(ValueError, match="empty split"):
        temporal_split(["2024-01-01"], 0.5)


def test_score_by_stratum_directness():
    cases = [
        UpdateCase("a", direct=True),
        UpdateCase("b", direct=True),
        UpdateCase("c", direct=False),
    ]
    result = score_by_stratum(cases, [True, False, True])
    assert set(result) == {"direct", "transitive"}
    assert result["direct"]["direct-dependency"].accuracy == 0.5
    assert result["transitive"]["direct-dependency"].accuracy == 0.0


def test_semver_stratum():
    assert semver_stratum(UpdateCase("a", "1.0.0", "2.0.0")) == "major"
    assert semver_stratum(UpdateCase("a", "1.0.0", "1.1.0")) == "non-major"
    assert directness_stratum(UpdateCase("a", direct=False)) == "transitive"


def test_score_by_stratum_length_mismatch():
    with pytest.raises(ValueError, match="length mismatch"):
        score_by_stratum([UpdateCase("a")], [True, False])
