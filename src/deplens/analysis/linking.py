from __future__ import annotations

import sys
from dataclasses import dataclass

from packaging.utils import canonicalize_name

from deplens.analysis.imports import ImportRecord

KNOWN_ALIASES = {
    "pil": "pillow",
    "yaml": "pyyaml",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
}


@dataclass(frozen=True)
class ImportLink:
    record: ImportRecord
    dependency: str | None
    stdlib: bool


def _norm(name: str) -> str:
    return canonicalize_name(name).replace("-", "_")


def is_stdlib(top_level: str) -> bool:
    return top_level in sys.stdlib_module_names


def link_imports(
    records: list[ImportRecord],
    dependency_names: list[str],
    aliases: dict[str, str] | None = None,
) -> list[ImportLink]:
    table = dict(KNOWN_ALIASES)
    if aliases:
        table.update(aliases)
    by_norm = {_norm(name): canonicalize_name(name) for name in dependency_names}
    links: list[ImportLink] = []
    for record in records:
        top = record.top_level()
        if not top:
            links.append(ImportLink(record, None, False))
            continue
        if is_stdlib(top):
            links.append(ImportLink(record, None, True))
            continue
        norm = _norm(top)
        dependency = by_norm.get(norm)
        if dependency is None and norm in table:
            candidate = canonicalize_name(table[norm])
            dependency = candidate if candidate in by_norm else None
        links.append(ImportLink(record, dependency, False))
    return links


def affected_imports(links: list[ImportLink], dependency: str) -> list[ImportLink]:
    key = canonicalize_name(dependency)
    return [link for link in links if link.dependency == key]
