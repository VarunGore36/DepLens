from __future__ import annotations

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


def run_command(workdir: str | Path, cmd: list[str], timeout: int) -> CommandResult:
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
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
) -> CommandResult:
    with tempfile.TemporaryDirectory(prefix="deplens-wt-") as dest:
        if not _worktree(repo, commit, dest):
            return CommandResult(None, None, f"worktree setup failed for {commit}")
        try:
            if setup is not None:
                prepared = run_command(dest, setup, timeout)
                if not prepared.passed:
                    return CommandResult(None, prepared.returncode, prepared.output)
            return run_command(dest, cmd, timeout)
        finally:
            _remove_worktree(repo, dest)


def label_test_outcomes(
    repo: str | Path,
    records: list[UpdateRecord],
    cmd: list[str],
    timeout: int = 300,
    setup: list[str] | None = None,
    limit: int | None = None,
) -> list[TestOutcome]:
    outcomes = []
    for record in records[:limit] if limit is not None else records:
        if not record.parent:
            outcomes.append(TestOutcome(record, None, None, "error"))
            continue
        parent = outcome_for_commit(repo, record.parent, cmd, timeout, setup)
        if parent.passed is None:
            outcomes.append(TestOutcome(record, None, None, "timeout" if parent.returncode is None else "error"))
            continue
        commit = outcome_for_commit(repo, record.commit, cmd, timeout, setup)
        if commit.passed is None:
            outcomes.append(TestOutcome(record, parent.passed, None, "timeout" if commit.returncode is None else "error"))
            continue
        if parent.passed and not commit.passed:
            label = "breaks-tests"
        elif not parent.passed:
            label = "already-failing"
        else:
            label = "passes"
        outcomes.append(TestOutcome(record, parent.passed, commit.passed, label))
    return outcomes
