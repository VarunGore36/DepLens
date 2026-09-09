from deplens.prediction import (
    ApiChange,
    EmptyApiDiffProvider,
    HybridWeights,
    UpdateCase,
    fit_grid,
    hybrid_predict,
    hybrid_score,
    llm_assisted_heuristic,
    removed_apis,
    signals,
)


def test_signals_and_score():
    case = UpdateCase("a", "1.0.0", "2.0.0", direct=True, depth=1, affected_imports=1)
    values = signals(case)
    assert values == {"major": 1.0, "direct": 1.0, "deep": 0.0, "api": 0.0, "usage": 1.0}
    assert hybrid_score(case, HybridWeights()) == 1.0
    assert hybrid_score(case, HybridWeights(0, 0, 0, 0, 0)) == 0.0
    assert hybrid_predict(case, HybridWeights()).label is True


def test_fit_grid_finds_separating_weights():
    cases = [
        UpdateCase("a", "1.0.0", "2.0.0", direct=False, depth=3, affected_imports=0),
        UpdateCase("b", "1.0.0", "1.0.1", direct=False, depth=3, affected_imports=0),
    ]
    weights = fit_grid(cases, [True, False])
    assert weights.major > 0
    assert [hybrid_predict(case, weights).label for case in cases] == [True, False]


def test_llm_adapter_seam():
    assert EmptyApiDiffProvider().diff("requests", "2.28.0", "2.31.0") == []
    changes = [ApiChange("requests.get", "removed"), ApiChange("requests.post", "changed")]
    assert [c.name for c in removed_apis(changes)] == ["requests.get"]
    assert llm_assisted_heuristic(UpdateCase("a"), changes).label is True
    assert llm_assisted_heuristic(UpdateCase("a"), []).label is False
    touched = UpdateCase("a", affected_apis=1)
    assert llm_assisted_heuristic(touched, [ApiChange("a.f", "changed")]).label is True
    assert llm_assisted_heuristic(UpdateCase("a"), [ApiChange("a.f", "changed")]).label is False
