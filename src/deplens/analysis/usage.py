from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from packaging.utils import canonicalize_name

from deplens.analysis.linking import KNOWN_ALIASES


@dataclass(frozen=True)
class UsageRecord:
    qualified: str
    top_level: str
    lineno: int = 0
    source: str | None = None
    is_call: bool = False


@dataclass
class ParsedUsage:
    usages: list[UsageRecord] = field(default_factory=list)
    files_scanned: int = 0

    def qualified_names(self) -> list[str]:
        seen: list[str] = []
        for usage in self.usages:
            if usage.qualified not in seen:
                seen.append(usage.qualified)
        return seen


def _build_symbols(tree: ast.AST) -> dict[str, str]:
    symbols: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    symbols[alias.asname.split(".")[0]] = alias.name
                else:
                    symbols[alias.name.split(".")[0]] = alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            if not node.module:
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                symbols[(alias.asname or alias.name).split(".")[0]] = f"{node.module}.{alias.name}"
    return symbols


def _resolve_chain(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _resolve_chain(node.value)
        if base is None:
            return None
        return f"{base}.{node.attr}"
    return None


class _UsageVisitor(ast.NodeVisitor):
    def __init__(self, symbols: dict[str, str], source: str) -> None:
        self.symbols = symbols
        self.source = source
        self.usages: list[UsageRecord] = []
        self.call_funcs: set[int] = set()
        self.skip_names: set[int] = set()
        self.skip_attrs: set[int] = set()

    def visit_Call(self, node: ast.Call) -> None:
        self.call_funcs.add(id(node.func))
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if id(node) in self.skip_attrs:
            self.generic_visit(node)
            return
        chain = _resolve_chain(node)
        if chain is not None:
            base = chain.split(".")[0]
            target = self.symbols.get(base)
            if target is not None:
                suffix = chain[len(base):]
                qualified = target + suffix
                inner: ast.AST = node
                while isinstance(inner, ast.Attribute):
                    self.skip_attrs.add(id(inner))
                    inner = inner.value
                if isinstance(inner, ast.Name):
                    self.skip_names.add(id(inner))
                self.usages.append(
                    UsageRecord(
                        qualified=qualified,
                        top_level=target.split(".")[0],
                        lineno=node.lineno,
                        source=self.source,
                        is_call=id(node) in self.call_funcs,
                    )
                )
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if id(node) not in self.skip_names and isinstance(node.ctx, ast.Load):
            target = self.symbols.get(node.id)
            if target is not None:
                self.usages.append(
                    UsageRecord(
                        qualified=target,
                        top_level=target.split(".")[0],
                        lineno=node.lineno,
                        source=self.source,
                        is_call=id(node) in self.call_funcs,
                    )
                )
        self.generic_visit(node)


def parse_usage_text(text: str, source: str = "<source>") -> ParsedUsage:
    try:
        tree = ast.parse(text, filename=source)
    except SyntaxError as exc:
        raise ValueError(f"{source}: invalid Python: {exc}") from exc
    visitor = _UsageVisitor(_build_symbols(tree), source)
    visitor.visit(tree)
    return ParsedUsage(visitor.usages)


def parse_usage_file(path: str | Path) -> ParsedUsage:
    p = Path(path)
    return parse_usage_text(p.read_text(encoding="utf-8"), source=str(p))


def collect_usage(root: str | Path) -> ParsedUsage:
    base = Path(root)
    if base.is_file():
        parsed = parse_usage_file(base)
        return ParsedUsage(list(parsed.usages), files_scanned=1)
    usages: list[UsageRecord] = []
    scanned = 0
    for path in sorted(base.rglob("*.py")):
        if any(part in (".venv", "venv", "__pycache__", ".git") for part in path.parts):
            continue
        parsed = parse_usage_file(path)
        usages.extend(parsed.usages)
        scanned += 1
    return ParsedUsage(usages, files_scanned=scanned)


def _norm(name: str) -> str:
    return canonicalize_name(name).replace("-", "_")


def usages_for_dependency(
    usages: list[UsageRecord],
    dependency: str,
    aliases: dict[str, str] | None = None,
) -> list[UsageRecord]:
    table = dict(KNOWN_ALIASES)
    if aliases:
        table.update(aliases)
    key = canonicalize_name(dependency)
    wanted = {_norm(dependency)}
    for top, dep in table.items():
        if canonicalize_name(dep) == key:
            wanted.add(_norm(top))
    return [u for u in usages if _norm(u.top_level) in wanted]
