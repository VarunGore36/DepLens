from deplens.dependencies import parse_requirements_text
from deplens.graph import (
    DependencyGraph,
    degree_centrality,
    fan_in,
    fan_out,
    node_features,
)


def _graph():
    graph = DependencyGraph.from_specs(
        parse_requirements_text("requests==2.28\nnumpy==1.26\n").specs
    )
    graph.add_edge("requests", "urllib3")
    return graph


def test_fan_in_out():
    graph = _graph()
    assert fan_in(graph)["urllib3"] == 1
    assert fan_in(graph)["requests"] == 1
    assert fan_out(graph)["requests"] == 1
    assert fan_out(graph)["numpy"] == 0


def test_degree_centrality_bounds():
    centrality = degree_centrality(_graph())
    assert all(0.0 <= value <= 1.0 for value in centrality.values())
    assert centrality["requests"] > centrality["numpy"]


def test_node_features():
    features = node_features(_graph())
    assert features["requests"]["depth"] == 1
    assert features["requests"]["direct"] is True
    assert features["urllib3"]["direct"] is False
    assert features["urllib3"]["fan_in"] == 1
