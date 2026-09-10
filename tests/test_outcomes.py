import subprocess
import sys
import tempfile

import pytest

from deplens.updates import (
    create_venv,
    detect_updates,
    install_worktree_deps,
    label_test_outcomes,
    label_test_outcomes_isolated,
    run_command,
)

PYTEST = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]


def _git(repo, *args):
    result = subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.fixture
def break_repo(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    (tmp_path / "test_x.py").write_text("def test_a():\n    assert True\n")
    _git(tmp_path, "add", "requirements.txt", "test_x.py")
    _git(tmp_path, "commit", "-qm", "initial")
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
    (tmp_path / "test_x.py").write_text("def test_a():\n    assert True\n")
    _git(tmp_path, "add", "requirements.txt", "test_x.py")
    _git(tmp_path, "commit", "-qm", "bump requests")
    (tmp_path / "requirements.txt").write_text("requests==2.32.0\n")
    (tmp_path / "test_x.py").write_text("def test_a():\n    assert False\n")
    _git(tmp_path, "add", "requirements.txt", "test_x.py")
    _git(tmp_path, "commit", "-qm", "bump requests, break test")
    return tmp_path


def test_run_command_pass_and_fail(tmp_path):
    assert run_command(tmp_path, [sys.executable, "-c", "pass"], 60).passed is True
    failed = run_command(tmp_path, [sys.executable, "-c", "raise SystemExit(1)"], 60)
    assert failed.passed is False and failed.returncode == 1


def test_run_command_timeout(tmp_path):
    result = run_command(tmp_path, [sys.executable, "-c", "import time; time.sleep(30)"], 1)
    assert result.passed is None and result.returncode is None


def test_label_test_outcomes(break_repo):
    records = detect_updates(break_repo)
    updates = [r for r in records if r.change == "updated"]
    assert len(updates) == 2
    outcomes = label_test_outcomes(break_repo, updates, PYTEST, timeout=120)
    by_subject = {o.update.subject: o for o in outcomes}
    assert by_subject["bump requests"].label == "passes"
    breaking = by_subject["bump requests, break test"]
    assert breaking.parent_passed is True and breaking.commit_passed is False
    assert breaking.label == "breaks-tests"


def test_label_test_outcomes_limit(break_repo):
    records = detect_updates(break_repo)
    assert [o.label for o in label_test_outcomes(break_repo, records, PYTEST, timeout=120, limit=0)] == []


def test_undecidable_codes_yield_no_tests(break_repo):
    records = detect_updates(break_repo)
    updates = [r for r in records if r.change == "updated"]
    exit5 = [sys.executable, "-c", "import sys; sys.exit(5)"]
    outcomes = label_test_outcomes(break_repo, updates, exit5, timeout=120, undecidable_codes=(5,))
    assert {o.label for o in outcomes} == {"no-tests"}


@pytest.fixture
def iso_repo(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    (tmp_path / "test_x.py").write_text("def test_a():\n    assert True\n")
    _git(tmp_path, "add", "requirements.txt", "test_x.py")
    _git(tmp_path, "commit", "-qm", "initial")
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
    (tmp_path / "test_x.py").write_text("def test_a():\n    assert False\n")
    _git(tmp_path, "add", "requirements.txt", "test_x.py")
    _git(tmp_path, "commit", "-qm", "bump dep, break test")
    return tmp_path


def test_create_venv_has_working_python(tmp_path):
    with tempfile.TemporaryDirectory() as base:
        result = create_venv(f"{base}/venv", sys.executable, 120)
        assert result.passed is True
        assert run_command(base, [result.output, "-c", "pass"], 60).passed is True


def test_install_worktree_deps_empty_requirements(tmp_path):
    (tmp_path / "requirements.txt").write_text("")
    with tempfile.TemporaryDirectory() as base:
        venv = create_venv(f"{base}/venv", sys.executable, 120)
        assert venv.passed is True
        installed = install_worktree_deps(venv.output, tmp_path, 180)
        assert installed.passed is True


def test_label_test_outcomes_isolated(iso_repo):
    records = [r for r in detect_updates(iso_repo) if r.change == "updated"]
    assert len(records) == 1
    outcomes = label_test_outcomes_isolated(
        iso_repo, records, ["-m", "pytest", "-q", "-p", "no:cacheprovider"], timeout=180
    )
    assert len(outcomes) == 1
    assert outcomes[0].parent_passed is True and outcomes[0].commit_passed is False
    assert outcomes[0].label == "breaks-tests"
