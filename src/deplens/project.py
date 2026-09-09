from __future__ import annotations

from pathlib import Path

from deplens.analysis.imports import collect_imports
from deplens.analysis.linking import link_imports
from deplens.analysis.usage import collect_usage
from deplens.dependencies.lockfiles import parse_lockfile_file
from deplens.dependencies.models import ParsedDependencies
from deplens.dependencies.pyproject import parse_pyproject_file
from deplens.dependencies.requirements import parse_requirements_file
from deplens.graph.features import node_features
from deplens.graph.model import DependencyGraph
from deplens.updates.detection import is_dep_file

SKIP_DIRS = (".venv", "venv", "__pycache__", ".git", ".tox", "node_modules")


def discover_dependency_files(root: str | Path) -> list[Path]:
    base = Path(root)
    found = []
    candidates = [base] if base.is_file() else sorted(base.rglob("*"))
    for path in candidates:
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name == "pyproject.toml" or is_dep_file(str(path)):
            found.append(path)
    return found


def _parse_file(path: Path) -> ParsedDependencies:
    if path.name == "pyproject.toml":
        return parse_pyproject_file(path)
    if path.name in ("poetry.lock", "uv.lock", "Pipfile.lock"):
        return parse_lockfile_file(path)
    return parse_requirements_file(path)


def analyze_project(root: str | Path) -> dict:
    base = Path(root)
    specs: list = []
    errors: list[str] = []
    files = discover_dependency_files(base)
    for path in files:
        try:
            specs.extend(_parse_file(path).specs)
        except ValueError as exc:
            errors.append(str(exc))
    graph = DependencyGraph.from_specs(specs, root=base.name if base.name else "project")
    directory = base if base.is_dir() else base.parent
    imports = collect_imports(directory)
    usages = collect_usage(directory)
    links = link_imports(imports.records, graph.direct_dependencies())
    linked = sum(1 for link in links if link.dependency is not None)
    stdlib = sum(1 for link in links if link.stdlib)
    return {
        "root": str(base),
        "dependency_files": [str(p) for p in files],
        "parse_errors": errors,
        "dependencies": graph.to_dict(),
        "node_features": node_features(graph),
        "imports": {
            "count": len(imports.records),
            "top_levels": imports.top_levels(),
            "linked": linked,
            "stdlib": stdlib,
            "unresolved": len(links) - linked - stdlib,
        },
        "usage": {
            "count": len(usages.usages),
            "qualified": usages.qualified_names(),
        },
    }
