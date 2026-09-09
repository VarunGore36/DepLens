import subprocess

import pytest

from deplens.updates import detect_updates, is_dep_file, updates_for_package


def _git(repo, *args):
    result = subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    _git(tmp_path, "add", "requirements.txt")
    _git(tmp_path, "commit", "-qm", "initial")
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\nnumpy==1.26.0\n")
    _git(tmp_path, "add", "requirements.txt")
    _git(tmp_path, "commit", "-qm", "bump requests, add numpy")
    (tmp_path / "app.py").write_text("x = 1\n")
    _git(tmp_path, "add", "app.py")
    _git(tmp_path, "commit", "-qm", "unrelated")
    return tmp_path


def test_is_dep_file():
    assert is_dep_file("requirements.txt")
    assert is_dep_file("subdir/requirements-dev.txt")
    assert is_dep_file("pyproject.toml")
    assert is_dep_file("poetry.lock")
    assert not is_dep_file("app.py")
    assert not is_dep_file("requirements.md")


def test_detect_updates(repo):
    records = detect_updates(repo)
    assert len(records) == 3
    bumped = updates_for_package(records, "requests")
    assert len(bumped) == 2
    updated = next(r for r in bumped if r.change == "updated")
    assert updated.old_constraint == "==2.28.0"
    assert updated.new_constraint == "==2.31.0"
    assert updated.file == "requirements.txt"
    added = updates_for_package(records, "numpy")
    assert len(added) == 1 and added[0].change == "added"


def test_non_git_dir_raises(tmp_path):
    with pytest.raises(ValueError, match="failed"):
        detect_updates(tmp_path)


def test_duplicate_lines_not_reported_as_update(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    _git(tmp_path, "add", "requirements.txt")
    _git(tmp_path, "commit", "-qm", "initial")
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\nrequests==2.28.0\n")
    _git(tmp_path, "add", "requirements.txt")
    _git(tmp_path, "commit", "-qm", "duplicate line")
    records = updates_for_package(detect_updates(tmp_path), "requests")
    assert [r for r in records if r.change == "updated"] == []


def test_marker_only_change_reported_as_update(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    _git(tmp_path, "add", "requirements.txt")
    _git(tmp_path, "commit", "-qm", "initial")
    (tmp_path / "requirements.txt").write_text("requests==2.28.0; python_version > '3.8'\n")
    _git(tmp_path, "add", "requirements.txt")
    _git(tmp_path, "commit", "-qm", "add marker")
    records = updates_for_package(detect_updates(tmp_path), "requests")
    updated = [r for r in records if r.change == "updated"]
    assert len(updated) == 1 and "python_version" in (updated[0].new_constraint or "")
