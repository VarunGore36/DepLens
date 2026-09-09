from __future__ import annotations

import json
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from packaging.utils import canonicalize_name

from deplens.dependencies.models import DependencySpec, ParsedDependencies
from deplens.dependencies.requirements import parse_requirements_text


def _loads_toml(text: str, source: str) -> dict:
    try:
        return tomllib.loads(text)
    except Exception as exc:
        raise ValueError(f"{source}: invalid TOML: {exc}") from exc


def _pinned(name: str, version: str, source: str) -> DependencySpec:
    version = version.strip()
    constraint = f"=={version}" if version and not version.startswith("==") else version
    return DependencySpec(
        name=canonicalize_name(name),
        raw=f"{name}{constraint}",
        constraint=constraint,
        source=source,
    )


def parse_poetry_lock_text(text: str, source: str = "poetry.lock") -> ParsedDependencies:
    data = _loads_toml(text, source)
    packages = data.get("package", [])
    if not isinstance(packages, list):
        raise ValueError(f"{source}: expected [[package]] list")  # noqa: TRY004
    specs = [
        _pinned(str(pkg["name"]), str(pkg.get("version", "")), f"{source}:package[{pkg.get('name')}]")
        for pkg in packages
        if isinstance(pkg, dict) and "name" in pkg
    ]
    return ParsedDependencies(specs)


def parse_uv_lock_text(text: str, source: str = "uv.lock") -> ParsedDependencies:
    data = _loads_toml(text, source)
    packages = data.get("package", [])
    if not isinstance(packages, list):
        raise ValueError(f"{source}: expected [[package]] list")  # noqa: TRY004
    specs = [
        _pinned(str(pkg["name"]), str(pkg.get("version", "")), f"{source}:package[{pkg.get('name')}]")
        for pkg in packages
        if isinstance(pkg, dict) and "name" in pkg
    ]
    return ParsedDependencies(specs)


def parse_pipfile_lock_text(text: str, source: str = "Pipfile.lock") -> ParsedDependencies:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source}: invalid JSON: {exc}") from exc
    specs: list[DependencySpec] = []
    for section in ("default", "develop"):
        entries = data.get(section, {}) or {}
        if not isinstance(entries, dict):
            raise ValueError(f"{source}: expected object for {section!r}")  # noqa: TRY004
        for name, meta in entries.items():
            version = ""
            if isinstance(meta, dict):
                version = str(meta.get("version", "") or "")
            specs.append(_pinned(str(name), version, f"{source}:{section}[{name}]"))
    return ParsedDependencies(specs)


def parse_lockfile_file(path: str | Path) -> ParsedDependencies:
    p = Path(path)
    name = p.name.lower()
    text = p.read_text(encoding="utf-8")
    if name == "poetry.lock":
        return parse_poetry_lock_text(text, source=str(p))
    if name == "uv.lock":
        return parse_uv_lock_text(text, source=str(p))
    if name == "pipfile.lock":
        return parse_pipfile_lock_text(text, source=str(p))
    return parse_requirements_text(text, source=str(p))
