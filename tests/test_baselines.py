from deplens.prediction import (
    UpdateCase,
    api_change_heuristic,
    coerce_version,
    depth_heuristic,
    direct_dependency_heuristic,
    major_version_heuristic,
    run_baselines,
    semver_change,
)


def test_semver_change():
    assert semver_change("1.2.3", "2.0.0") == "major"
    assert semver_change("1.2.3", "1.3.0") == "minor"
    assert semver_change("1.2.3", "1.2.4") == "patch"
    assert semver_change("1.2.3", "1.2.3") == "other"
    assert semver_change(None, "1.0.0") == "unknown"
    assert semver_change("not-a-version", "1.0.0") == "unknown"


def test_coerce_version():
    assert coerce_version("==2.31.0") == "2.31.0"
    assert coerce_version(">=2,<3") is None
    assert coerce_version(None) is None
    assert coerce_version("") is None


def test_major_version_heuristic():
    assert major_version_heuristic(UpdateCase("a", "1.0.0", "2.0.0")).label is True
    assert major_version_heuristic(UpdateCase("a", "1.0.0", "1.1.0")).label is False


def test_direct_dependency_heuristic():
    assert direct_dependency_heuristic(UpdateCase("a", direct=True)).label is True
    assert direct_dependency_heuristic(UpdateCase("a", direct=False)).label is False


def test_api_change_heuristic():
    assert api_change_heuristic(UpdateCase("a", api_changed=True)).label is True
    assert api_change_heuristic(UpdateCase("a", api_changed=False)).label is False
    assert api_change_heuristic(UpdateCase("a", api_changed=None)).label is False


def test_depth_heuristic():
    assert depth_heuristic(UpdateCase("a", depth=3)).label is True
    assert depth_heuristic(UpdateCase("a", depth=1)).label is False
    assert depth_heuristic(UpdateCase("a", depth=None)).label is True


def test_run_baselines_returns_all_rules():
    predictions = run_baselines(UpdateCase("a", "1.0.0", "2.0.0", direct=True, depth=1))
    assert sorted(p.rule for p in predictions) == [
        "api-change",
        "dependency-depth",
        "direct-dependency",
        "major-version",
    ]
