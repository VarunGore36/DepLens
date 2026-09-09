from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from deplens.dependencies.models import DependencySpec, ParsedDependencies


def _from_pep508(raw: str, source: str) -> DependencySpec:
    try:
        req = Requirement(raw)
    except InvalidRequirement as exc:
        raise ValueError(f"{source}: invalid requirement {raw!r}: {exc}") from exc
    return DependencySpec(
        name=canonicalize_name(req.name),
        raw=raw,
        constraint=str(req.specifier),
        extras=tuple(sorted(req.extras)),
        marker=str(req.marker) if req.marker is not None else None,
        url=req.url,
        source=source,
    )


def _from_poetry_entry(name: str, entry: object, source: str) -> DependencySpec | None:
    if canonicalize_name(name) == "python":
        return None
    if isinstance(entry, str):
        constraint = entry.strip()
        extras: tuple[str, ...] = ()
        marker = None
        url = None
        raw = f"{name} {constraint}".strip() if constraint != "*" else name
    elif isinstance(entry, dict):
        version = str(entry.get("version", "")).strip()
        raw_extras = entry.get("extras", [])
        extras = tuple(sorted(str(e) for e in raw_extras)) if isinstance(raw_extras, list) else ()
        markers = entry.get("markers")
        marker = str(markers) if markers is not None else None
        git = entry.get("git")
        path = entry.get("path")
        url = str(git) if git is not None else (str(path) if path is not None else None)
        constraint = version if version != "*" else ""
        raw = f"{name} {constraint}".strip() if constraint else name
    elif isinstance(entry, list):
        raise ValueError(f"{source}: multi-constraint poetry entry for {name!r} not supported in Phase 1")  # noqa: TRY004
    else:
        raise ValueError(f"{source}: unsupported poetry entry for {name!r}: {entry!r}")  # noqa: TRY004
    return DependencySpec(
        name=canonicalize_name(name),
        raw=raw,
        constraint="" if constraint == "*" else constraint,
        extras=extras,
        marker=marker,
        url=url,
        source=source,
    )


def parse_pyproject_text(text: str, source: str = "pyproject.toml") -> ParsedDependencies:
    try:
        data = tomllib.loads(text)
    except Exception as exc:
        raise ValueError(f"{source}: invalid TOML: {exc}") from exc
    return parse_pyproject_data(data, source=source)


def parse_pyproject_data(data: dict, source: str = "pyproject.toml") -> ParsedDependencies:
    specs: list[DependencySpec] = []
    project = data.get("project", {})
    if isinstance(project, dict):
        for raw in project.get("dependencies", []) or []:
            specs.append(_from_pep508(str(raw), f"{source}:project.dependencies"))
        optional = project.get("optional-dependencies", {}) or {}
        if isinstance(optional, dict):
            for group, items in optional.items():
                for raw in items or []:
                    specs.append(_from_pep508(str(raw), f"{source}:project.optional-dependencies[{group}]"))
    tool = data.get("tool", {})
    poetry = tool.get("poetry", {}) if isinstance(tool, dict) else {}
    if isinstance(poetry, dict):
        deps = poetry.get("dependencies", {}) or {}
        if isinstance(deps, dict):
            for name, entry in deps.items():
                spec = _from_poetry_entry(str(name), entry, f"{source}:tool.poetry.dependencies")
                if spec is not None:
                    specs.append(spec)
        group = poetry.get("group", {}) or {}
        if isinstance(group, dict):
            for group_name, group_data in group.items():
                group_deps = group_data.get("dependencies", {}) if isinstance(group_data, dict) else {}
                if isinstance(group_deps, dict):
                    for name, entry in group_deps.items():
                        spec = _from_poetry_entry(
                            str(name), entry, f"{source}:tool.poetry.group[{group_name}]"
                        )
                        if spec is not None:
                            specs.append(spec)
    return ParsedDependencies(specs)


def parse_pyproject_file(path: str | Path) -> ParsedDependencies:
    p = Path(path)
    return parse_pyproject_text(p.read_text(encoding="utf-8"), source=str(p))
