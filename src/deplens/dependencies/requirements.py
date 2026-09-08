from __future__ import annotations

from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from deplens.dependencies.models import DependencySpec, ParsedDependencies


def _strip_inline_comment(line: str) -> str:
    for sep in (" #", "\t#"):
        idx = line.find(sep)
        if idx != -1:
            return line[:idx].rstrip()
    return line


def parse_requirements_text(text: str, source: str = "requirements.txt") -> ParsedDependencies:
    specs: list[DependencySpec] = []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-"):
            continue
        line = _strip_inline_comment(line).strip()
        if not line:
            continue
        try:
            req = Requirement(line)
        except InvalidRequirement as exc:
            raise ValueError(f"{source}:{lineno}: invalid requirement {raw_line!r}: {exc}") from exc
        specs.append(
            DependencySpec(
                name=canonicalize_name(req.name),
                raw=line,
                constraint=str(req.specifier),
                extras=tuple(sorted(req.extras)),
                marker=str(req.marker) if req.marker is not None else None,
                url=req.url,
                source=f"{source}:{lineno}",
            )
        )
    return ParsedDependencies(specs)


def parse_requirements_file(path: str | Path) -> ParsedDependencies:
    p = Path(path)
    return parse_requirements_text(p.read_text(encoding="utf-8"), source=str(p))
