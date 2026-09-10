from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from deplens.updates.detection import UpdateRecord

OUTPUT_LIMIT = 4000


@dataclass(frozen=True)
class CommandResult:
    passed: bool | None
    returncode: int | None
    output: str


@dataclass(frozen=True)
class TestOutcome:
    update: UpdateRecord
    parent_passed: bool | None
    commit_passed: bool | None
    label: str


def run_command(
    workdir: str | Path,
    cmd: list[str],
    timeout: int,
    env: dict[str, str] | None = None,
) -> CommandResult:
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env={**os.environ, **(env or {})},
        )
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + (exc.stderr or "")
        return CommandResult(None, None, str(output)[-OUTPUT_LIMIT:])
    output = (completed.stdout + completed.stderr)[-OUTPUT_LIMIT:]
    return CommandResult(completed.returncode == 0, completed.returncode, output)


def _worktree(repo: str | Path, commit: str, dest: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", "--detach", dest, commit],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _remove_worktree(repo: str | Path, dest: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "remove", "--force", dest],
        capture_output=True,
        text=True,
        check=False,
    )


def outcome_for_commit(
    repo: str | Path,
    commit: str,
    cmd: list[str],
    timeout: int = 300,
    setup: list[str] | None = None,
    env: dict[str, str] | None = None,
    prepend_src: bool = False,
) -> CommandResult:
    with tempfile.TemporaryDirectory(prefix="deplens-wt-") as dest:
        if not _worktree(repo, commit, dest):
            return CommandResult(None, None, f"worktree setup failed for {commit}")
        if prepend_src:
            src = str(Path(dest) / "src")
            base = dict(env or {})
            base["PYTHONPATH"] = src + os.pathsep + base.get("PYTHONPATH", os.environ.get("PYTHONPATH", ""))
            env = base
        try:
            if setup is not None:
                prepared = run_command(dest, setup, timeout, env)
                if not prepared.passed:
                    return CommandResult(None, prepared.returncode, prepared.output)
            return run_command(dest, cmd, timeout, env)
        finally:
            _remove_worktree(repo, dest)


def label_test_outcomes(
    repo: str | Path,
    records: list[UpdateRecord],
    cmd: list[str],
    timeout: int = 300,
    setup: list[str] | None = None,
    limit: int | None = None,
    env: dict[str, str] | None = None,
    prepend_src: bool = False,
    undecidable_codes: tuple[int, ...] = (),
) -> list[TestOutcome]:
    outcomes = []
    for record in records[:limit] if limit is not None else records:
        if not record.parent:
            outcomes.append(TestOutcome(record, None, None, "error"))
            continue
        parent = outcome_for_commit(repo, record.parent, cmd, timeout, setup, env, prepend_src)
        if parent.passed is None:
            outcomes.append(TestOutcome(record, None, None, "timeout" if parent.returncode is None else "error"))
            continue
        if parent.returncode in undecidable_codes:
            outcomes.append(TestOutcome(record, None, None, "no-tests"))
            continue
        commit = outcome_for_commit(repo, record.commit, cmd, timeout, setup, env, prepend_src)
        if commit.passed is None:
            outcomes.append(TestOutcome(record, parent.passed, None, "timeout" if commit.returncode is None else "error"))
            continue
        if commit.returncode in undecidable_codes:
            outcomes.append(TestOutcome(record, parent.passed, None, "no-tests"))
            continue
        if parent.passed and not commit.passed:
            label = "breaks-tests"
        elif not parent.passed:
            label = "already-failing"
        else:
            label = "passes"
        outcomes.append(TestOutcome(record, parent.passed, commit.passed, label))
    return outcomes
