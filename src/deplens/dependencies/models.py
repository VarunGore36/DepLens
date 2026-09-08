from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DependencySpec:
    name: str
    raw: str
    constraint: str = ""
    extras: tuple[str, ...] = ()
    marker: str | None = None
    url: str | None = None
    source: str | None = None


@dataclass
class ParsedDependencies:
    specs: list[DependencySpec] = field(default_factory=list)

    def by_name(self) -> dict[str, list[DependencySpec]]:
        grouped: dict[str, list[DependencySpec]] = {}
        for spec in self.specs:
            grouped.setdefault(spec.name, []).append(spec)
        return grouped

    def names(self) -> list[str]:
        seen: list[str] = []
        for spec in self.specs:
            if spec.name not in seen:
                seen.append(spec.name)
        return seen
