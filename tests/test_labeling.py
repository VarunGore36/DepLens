import subprocess

import pytest

from deplens.updates import detect_updates, label_reverts, label_updates


def _git(repo, *args):
    result = subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.fixture
def revert_repo(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    _git(tmp_path, "add", "requirements.txt")
    _git(tmp_path, "commit", "-qm", "initial")
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
    _git(tmp_path, "add", "requirements.txt")
    _git(tmp_path, "commit", "-qm", "bump requests")
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    _git(tmp_path, "add", "requirements.txt")
    _git(tmp_path, "commit", "-qm", "revert requests bump, it broke auth")
    return tmp_path


@pytest.fixture
def fix_repo(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "requirements.txt").write_text("django==4.1.0\n")
    _git(tmp_path, "add", "requirements.txt")
    _git(tmp_path, "commit", "-qm", "initial")
    (tmp_path / "requirements.txt").write_text("django==4.2.0\n")
    _git(tmp_path, "add", "requirements.txt")
    _git(tmp_path, "commit", "-qm", "bump django")
    (tmp_path / "requirements.txt").write_text("django==4.2.0\n# workaround for 4.2\n")
    (tmp_path / "app.py").write_text("x = 1\n")
    _git(tmp_path, "add", "requirements.txt", "app.py")
    _git(tmp_path, "commit", "-qm", "fix compatibility with new django")
    return tmp_path


def test_label_reverts(revert_repo):
    records = detect_updates(revert_repo)
    bumped = [r for r in records if r.package == "requests" and r.change == "updated"]
    assert len(bumped) == 2
    labels = label_updates(revert_repo, records)
    by_commit = {label.update.commit: label for label in labels}
    assert by_commit[bumped[0].commit].label == "no-signal"
    assert by_commit[bumped[1].commit].label == "reverted"


def test_label_fix_suspect(fix_repo):
    records = detect_updates(fix_repo)
    labels = label_updates(fix_repo, records)
    bumped = [label for label in labels if label.update.change == "updated"]
    assert len(bumped) == 1
    assert bumped[0].label == "fix-suspect"


def test_label_reverts_pure_function(revert_repo):
    records = detect_updates(revert_repo)
    evidence = label_reverts(records)
    assert len(evidence) == 1
