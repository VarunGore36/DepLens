from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ImportRecord:
    kind: str
    module: str
    names: tuple[str, ...] = ()
    level: int = 0
    lineno: int = 0
    source: str | None = None

    def top_level(self) -> str:
        if not self.module:
            return ""
        return self.module.split(".")[0]


@dataclass
class ParsedImports:
    records: list[ImportRecord] = field(default_factory=list)
    files_scanned: int = 0

    def top_levels(self) -> list[str]:
        seen: list[str] = []
        for record in self.records:
            top = record.top_level()
            if top and top not in seen:
                seen.append(top)
        return seen


def parse_imports_text(text: str, source: str = "<source>") -> ParsedImports:
    try:
        tree = ast.parse(text, filename=source)
    except SyntaxError as exc:
        raise ValueError(f"{source}: invalid Python: {exc}") from exc
    records: list[ImportRecord] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                records.append(
                    ImportRecord(
                        kind="import",
                        module=alias.name,
                        names=(alias.asname or alias.name,),
                        lineno=node.lineno,
                        source=source,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            records.append(
                ImportRecord(
                    kind="from",
                    module=node.module or "",
                    names=tuple(a.name for a in node.names),
                    level=node.level,
                    lineno=node.lineno,
                    source=source,
                )
            )
    return ParsedImports(records)


def parse_imports_file(path: str | Path) -> ParsedImports:
    p = Path(path)
    return parse_imports_text(p.read_text(encoding="utf-8"), source=str(p))


def collect_imports(root: str | Path) -> ParsedImports:
    base = Path(root)
    if base.is_file():
        parsed = parse_imports_file(base)
        return ParsedImports(list(parsed.records), files_scanned=1)
    records: list[ImportRecord] = []
    scanned = 0
    for path in sorted(base.rglob("*.py")):
        if any(part in (".venv", "venv", "__pycache__", ".git") for part in path.parts):
            continue
        parsed = parse_imports_file(path)
        records.extend(parsed.records)
        scanned += 1
    return ParsedImports(records, files_scanned=scanned)
