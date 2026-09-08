from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from packaging.utils import canonicalize_name

from deplens.dependencies.models import DependencySpec


@dataclass
class DependencyNode:
    name: str
    constraints: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    direct: bool = True

    def primary_constraint(self) -> str:
        return self.constraints[0] if self.constraints else ""


class DependencyGraph:
    def __init__(self, root: str = "project") -> None:
        self.root = canonicalize_name(root)
        self.nodes: dict[str, DependencyNode] = {}
        self.edges: dict[str, set[str]] = {self.root: set()}

    def add_spec(self, spec: DependencySpec, parent: str | None = None) -> str:
        key = canonicalize_name(spec.name)
        node = self.nodes.get(key)
        if node is None:
            node = DependencyNode(name=key, direct=parent is None or parent == self.root)
            self.nodes[key] = node
        if spec.constraint and spec.constraint not in node.constraints:
            node.constraints.append(spec.constraint)
        if spec.source and spec.source not in node.sources:
            node.sources.append(spec.source)
        origin = canonicalize_name(parent) if parent is not None else self.root
        self.edges.setdefault(origin, set()).add(key)
        self.edges.setdefault(key, set())
        return key

    def add_edge(self, parent: str, child: str) -> None:
        p = canonicalize_name(parent)
        c = canonicalize_name(child)
        for key in (p, c):
            if key != self.root and key not in self.nodes:
                self.nodes[key] = DependencyNode(name=key, direct=False)
        self.edges.setdefault(p, set()).add(c)
        self.edges.setdefault(c, set())
        if c in self.nodes and p != self.root:
            self.nodes[c].direct = False

    @classmethod
    def from_specs(cls, specs: list[DependencySpec], root: str = "project") -> DependencyGraph:
        graph = cls(root=root)
        for spec in specs:
            graph.add_spec(spec)
        return graph

    def direct_dependencies(self) -> list[str]:
        return sorted(self.edges.get(self.root, set()))

    def dependencies_of(self, name: str) -> list[str]:
        return sorted(self.edges.get(canonicalize_name(name), set()))

    def dependents_of(self, name: str) -> list[str]:
        key = canonicalize_name(name)
        return sorted(parent for parent, children in self.edges.items() if key in children)

    def depth(self, name: str) -> int | None:
        target = canonicalize_name(name)
        if target == self.root:
            return 0
        visited = {self.root}
        queue: deque[tuple[str, int]] = deque([(self.root, 0)])
        while queue:
            current, dist = queue.popleft()
            for child in self.edges.get(current, ()):
                if child == target:
                    return dist + 1
                if child not in visited:
                    visited.add(child)
                    queue.append((child, dist + 1))
        return None

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "nodes": {
                name: {
                    "constraints": node.constraints,
                    "sources": node.sources,
                    "direct": node.direct,
                    "depth": self.depth(name),
                }
                for name, node in sorted(self.nodes.items())
            },
            "edges": {parent: sorted(children) for parent, children in sorted(self.edges.items())},
        }

    def __len__(self) -> int:
        return len(self.nodes)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and canonicalize_name(name) in self.nodes
