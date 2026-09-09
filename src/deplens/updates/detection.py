from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from packaging.utils import canonicalize_name

from deplens.dependencies.lockfiles import (
    parse_pipfile_lock_text,
    parse_poetry_lock_text,
    parse_uv_lock_text,
)
from deplens.dependencies.pyproject import parse_pyproject_text
from deplens.dependencies.requirements import parse_requirements_text


@dataclass(frozen=True)
class UpdateRecord:
    commit: str
    parent: str
    date: str
    subject: str
    file: str
    package: str
    old_constraint: str | None
    new_constraint: str | None
    change: str


def _run_git(repo: str | Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def is_dep_file(path: str) -> bool:
    name = Path(path).name
    if name in ("pyproject.toml", "poetry.lock", "uv.lock", "Pipfile.lock"):
        return True
    return name.startswith("requirements") and Path(name).suffix in (".txt", ".in", ".lock")


def list_commits(repo: str | Path, max_count: int | None = None) -> list[tuple[str, str, str, str]]:
    args = ["log", "--pretty=format:%H%x1f%P%x1f%aI%x1f%s"]
    if max_count is not None:
        args.append(f"--max-count={max_count}")
    output = _run_git(repo, *args)
    commits = []
    for line in output.splitlines():
        parts = line.split("\x1f")
        if len(parts) != 4:
            continue
        sha, parents, date, subject = parts
        commits.append((sha, parents.split()[0] if parents else "", date, subject))
    return commits


def files_changed(repo: str | Path, sha: str, parent: str) -> list[str]:
    if parent:
        output = _run_git(repo, "diff", "--name-only", parent, sha)
    else:
        output = _run_git(repo, "ls-tree", "-r", "--name-only", sha)
    return [line for line in output.splitlines() if line]


def show_file(repo: str | Path, rev: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{rev}:{path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def parse_side(filename: str, text: str, source: str) -> dict[str, str] | None:
    name = Path(filename).name
    try:
        if name == "poetry.lock":
            parsed = parse_poetry_lock_text(text, source)
        elif name == "uv.lock":
            parsed = parse_uv_lock_text(text, source)
        elif name == "Pipfile.lock":
            parsed = parse_pipfile_lock_text(text, source)
        elif name == "pyproject.toml":
            parsed = parse_pyproject_text(text, source)
        else:
            parsed = parse_requirements_text(text, source)
    except ValueError:
        return None
    grouped: dict[str, str] = {}
    for dep_name, specs in parsed.by_name().items():
        parts = set()
        for spec in specs:
            part = spec.constraint
            if spec.extras:
                part += f"[{','.join(spec.extras)}]"
            if spec.marker:
                part += f"; {spec.marker}"
            parts.add(part)
        grouped[dep_name] = "|".join(sorted(parts))
    return grouped


def detect_updates(repo: str | Path, max_count: int | None = None) -> list[UpdateRecord]:
    records: list[UpdateRecord] = []
    for sha, parent, date, subject in list_commits(repo, max_count):
        changed = [f for f in files_changed(repo, sha, parent) if is_dep_file(f)]
        for path in changed:
            old_text = show_file(repo, parent, path) if parent else None
            new_text = show_file(repo, sha, path)
            old = parse_side(path, old_text, f"{sha}^:{path}") if old_text is not None else {}
            new = parse_side(path, new_text, f"{sha}:{path}") if new_text is not None else {}
            if old is None or new is None:
                continue
            for package in sorted(set(old) | set(new)):
                before = old.get(package)
                after = new.get(package)
                if before == after:
                    continue
                if before is None:
                    change = "added"
                elif after is None:
                    change = "removed"
                else:
                    change = "updated"
                records.append(
                    UpdateRecord(
                        commit=sha,
                        parent=parent,
                        date=date,
                        subject=subject,
                        file=path,
                        package=package,
                        old_constraint=before,
                        new_constraint=after,
                        change=change,
                    )
                )
    return records


def updates_for_package(records: list[UpdateRecord], package: str) -> list[UpdateRecord]:
    key = canonicalize_name(package)
    return [r for r in records if r.package == key]
