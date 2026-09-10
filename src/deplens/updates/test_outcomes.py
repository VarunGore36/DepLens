from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from deplens.updates.detection import UpdateRecord

OUTPUT_LIMIT = 4000
TEST_EXTRA_NAMES = ("test", "tests", "testing", "dev")


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


def _derive_label(parent_passed: bool, commit_passed: bool) -> str:
    if parent_passed and not commit_passed:
        return "breaks-tests"
    if not parent_passed:
        return "already-failing"
    return "passes"


def create_venv(dest: str | Path, python: str | None = None, timeout: int = 300) -> CommandResult:
    target = Path(dest)
    completed = run_command(
        target.parent, [python or sys.executable, "-m", "venv", str(target)], timeout
    )
    if not completed.passed:
        return CommandResult(None, completed.returncode, completed.output)
    candidate = target / ("Scripts" if os.name == "nt" else "bin") / "python"
    if not candidate.exists():
        return CommandResult(None, 1, f"venv python missing at {candidate}")
    return CommandResult(True, 0, str(candidate))


def _test_extra(base: Path) -> str | None:
    pyproject = base / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    groups = (data.get("project", {}) or {}).get("optional-dependencies", {}) or {}
    for name in TEST_EXTRA_NAMES:
        if name in groups:
            return name
    return None


def install_worktree_deps(venv_python: str, worktree: str | Path, timeout: int = 600) -> CommandResult:
    base = Path(worktree)
    steps = []
    if (base / "requirements.txt").exists():
        steps.append([venv_python, "-m", "pip", "install", "--quiet", "-r", "requirements.txt"])
    if (base / "pyproject.toml").exists() or (base / "setup.py").exists() or (base / "setup.cfg").exists():
        extra = _test_extra(base)
        target = f".[{extra}]" if extra else "."
        steps.append([venv_python, "-m", "pip", "install", "--quiet", "-e", target])
    for step in steps:
        result = run_command(base, step, timeout)
        if not result.passed:
            return result
    return CommandResult(True, 0, "")


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
        if parent.passed is None or parent.returncode in undecidable_codes:
            outcomes.append(_settle(record, parent, CommandResult(None, None, ""), undecidable_codes))
            continue
        commit = outcome_for_commit(repo, record.commit, cmd, timeout, setup, env, prepend_src)
        outcomes.append(_settle(record, parent, commit, undecidable_codes))
    return outcomes


def outcome_for_commit_isolated(
    repo: str | Path,
    commit: str,
    test_args: list[str],
    timeout: int = 300,
    install_timeout: int = 600,
    python: str | None = None,
) -> CommandResult:
    with tempfile.TemporaryDirectory(prefix="deplens-iso-") as base:
        worktree = str(Path(base) / "wt")
        if not _worktree(repo, commit, worktree):
            return CommandResult(None, None, f"worktree setup failed for {commit}")
        try:
            venv = create_venv(str(Path(base) / "venv"), python, timeout)
            if not venv.passed:
                return CommandResult(None, venv.returncode, venv.output)
            venv_python = venv.output
            installed = install_worktree_deps(venv_python, worktree, install_timeout)
            if not installed.passed:
                return CommandResult(None, installed.returncode, installed.output)
            if test_args[:2] == ["-m", "pytest"]:
                runner = run_command(
                    worktree, [venv_python, "-m", "pip", "install", "--quiet", "pytest"], install_timeout
                )
                if not runner.passed:
                    return CommandResult(None, runner.returncode, runner.output)
            src = Path(worktree) / "src"
            env = {"PYTHONPATH": str(src)} if src.is_dir() else None
            return run_command(worktree, [venv_python, *test_args], timeout, env)
        finally:
            _remove_worktree(repo, worktree)


def _settle(
    record: UpdateRecord,
    parent: CommandResult,
    commit: CommandResult,
    undecidable_codes: tuple[int, ...],
) -> TestOutcome:
    if parent.passed is None:
        return TestOutcome(record, None, None, "timeout" if parent.returncode is None else "error")
    if parent.returncode in undecidable_codes:
        return TestOutcome(record, None, None, "no-tests")
    if commit.passed is None:
        return TestOutcome(record, parent.passed, None, "timeout" if commit.returncode is None else "error")
    if commit.returncode in undecidable_codes:
        return TestOutcome(record, parent.passed, None, "no-tests")
    return TestOutcome(record, parent.passed, commit.passed, _derive_label(parent.passed, commit.passed))


def label_test_outcomes_isolated(
    repo: str | Path,
    records: list[UpdateRecord],
    test_args: list[str],
    timeout: int = 300,
    install_timeout: int = 600,
    limit: int | None = None,
    undecidable_codes: tuple[int, ...] = (),
) -> list[TestOutcome]:
    outcomes = []
    for record in records[:limit] if limit is not None else records:
        if not record.parent:
            outcomes.append(TestOutcome(record, None, None, "error"))
            continue
        parent = outcome_for_commit_isolated(repo, record.parent, test_args, timeout, install_timeout)
        if parent.passed is None or parent.returncode in undecidable_codes:
            outcomes.append(_settle(record, parent, CommandResult(None, None, ""), undecidable_codes))
            continue
        commit = outcome_for_commit_isolated(repo, record.commit, test_args, timeout, install_timeout)
        outcomes.append(_settle(record, parent, commit, undecidable_codes))
    return outcomes
