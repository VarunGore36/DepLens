from deplens.dependencies import parse_requirements_text
from deplens.graph import DependencyGraph


def test_from_specs_and_depth():
    parsed = parse_requirements_text("requests>=2\nnumpy==1.26\n")
    graph = DependencyGraph.from_specs(parsed.specs, root="demo")
    assert len(graph) == 2
    assert "requests" in graph
    assert graph.direct_dependencies() == ["numpy", "requests"]
    assert graph.depth("requests") == 1
    assert graph.depth("demo") == 0
    assert graph.depth("missing") is None


def test_transitive_edges_and_dependents():
    graph = DependencyGraph(root="demo")
    parsed = parse_requirements_text("requests>=2\n")
    for spec in parsed.specs:
        graph.add_spec(spec)
    graph.add_edge("requests", "urllib3")
    assert graph.depth("urllib3") == 2
    assert graph.dependencies_of("requests") == ["urllib3"]
    assert graph.dependents_of("urllib3") == ["requests"]
    snapshot = graph.to_dict()
    assert snapshot["root"] == "demo"
    assert snapshot["nodes"]["urllib3"]["depth"] == 2
    assert snapshot["nodes"]["requests"]["direct"] is True
    assert snapshot["nodes"]["urllib3"]["direct"] is False
