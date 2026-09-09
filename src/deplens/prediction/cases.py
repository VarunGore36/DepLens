from __future__ import annotations

from packaging.utils import canonicalize_name

from deplens.analysis.linking import ImportLink, affected_imports
from deplens.analysis.usage import UsageRecord, usages_for_dependency
from deplens.graph.model import DependencyGraph
from deplens.prediction.baselines import UpdateCase, coerce_version


def build_case(
    package: str,
    old_constraint: str | None,
    new_constraint: str | None,
    graph: DependencyGraph,
    links: list[ImportLink] | None = None,
    usages: list[UsageRecord] | None = None,
    api_changed: bool | None = None,
) -> UpdateCase:
    key = canonicalize_name(package)
    node = graph.nodes.get(key)
    return UpdateCase(
        package=key,
        old_version=coerce_version(old_constraint),
        new_version=coerce_version(new_constraint),
        direct=node.direct if node is not None else key in graph.direct_dependencies(),
        depth=graph.depth(key),
        api_changed=api_changed,
        affected_imports=len(affected_imports(links, key)) if links is not None else 0,
        affected_apis=len(
            {u.qualified for u in usages_for_dependency(usages, key)}
        ) if usages is not None else 0,
    )
