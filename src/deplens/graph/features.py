from __future__ import annotations

from deplens.graph.model import DependencyGraph


def fan_in(graph: DependencyGraph) -> dict[str, int]:
    return {name: len(graph.dependents_of(name)) for name in graph.nodes}


def fan_out(graph: DependencyGraph) -> dict[str, int]:
    return {name: len(graph.dependencies_of(name)) for name in graph.nodes}


def degree_centrality(graph: DependencyGraph) -> dict[str, float]:
    population = len(graph.nodes)
    if population < 2:
        return {name: 0.0 for name in graph.nodes}
    undirected: dict[str, set[str]] = {name: set() for name in graph.nodes}
    undirected.setdefault(graph.root, set())
    for parent, children in graph.edges.items():
        for child in children:
            undirected.setdefault(parent, set()).add(child)
            undirected.setdefault(child, set()).add(parent)
    scale = len(undirected) - 1
    return {
        name: len(undirected.get(name, set())) / scale for name in graph.nodes
    }


def node_features(graph: DependencyGraph) -> dict[str, dict[str, float | int | bool]]:
    centrality = degree_centrality(graph)
    incoming = fan_in(graph)
    outgoing = fan_out(graph)
    return {
        name: {
            "depth": graph.depth(name),
            "direct": node.direct,
            "fan_in": incoming[name],
            "fan_out": outgoing[name],
            "degree_centrality": centrality[name],
        }
        for name, node in graph.nodes.items()
    }
