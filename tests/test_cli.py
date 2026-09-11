import json
import subprocess

import pytest

import deplens
from deplens.cli import main


def _project(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    (tmp_path / "app.py").write_text("import requests\nrequests.get('https://x.test')\n")
    return tmp_path


def test_default_no_args(tmp_path, monkeypatch, capsys):
    _project(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "DepLens — default" in out
    assert "Dependencies: 1 packages" in out
    assert "not a git repository" in out


def test_default_dot_and_explicit_path(tmp_path, capsys, monkeypatch):
    _project(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["."]) == 0
    assert "Repository: " in capsys.readouterr().out
    assert main([str(tmp_path)]) == 0


def test_default_invalid_path(capsys):
    assert main(["/no/such/dir"]) == 2
    assert "no such path" in capsys.readouterr().err
    with pytest.raises(SystemExit) as exc:
        main(["a", "b"])
    assert exc.value.code == 2


def test_default_with_git_history(tmp_path, capsys):
    _project(tmp_path)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "-C", str(tmp_path),
         "commit", "-qm", "bump"],
        check=True,
    )
    assert main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "Recent updates: 1" in out
    assert "requests" in out


def test_quick_and_full(tmp_path, capsys):
    _project(tmp_path)
    assert main(["quick", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "DepLens — quick" in out
    assert "Recent updates: none found" in out
    assert main(["full", str(tmp_path)]) == 0
    assert "DepLens — full" in capsys.readouterr().out


def test_dependencies_and_usage(tmp_path, capsys):
    _project(tmp_path)
    assert main(["dependencies", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "requests ==2.28.0 (direct)" in out
    assert main(["usage", str(tmp_path), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["imports"]["count"] == 1
    assert main(["usage", str(tmp_path / "nope")]) == 2


def test_output_writes_file(tmp_path, capsys):
    _project(tmp_path)
    target = tmp_path / "report.md"
    assert main(["quick", str(tmp_path), "--output", str(target)]) == 0
    assert f"Report written to {target}" in capsys.readouterr().out
    assert "DepLens — quick" in target.read_text()


def test_format_json_default(tmp_path, capsys):
    _project(tmp_path)
    assert main([str(tmp_path), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["imports"]["count"] == 1


def test_help_and_version(capsys):
    with pytest.raises(SystemExit) as help_exit:
        main(["--help"])
    assert help_exit.value.code == 0
    assert "quick" in capsys.readouterr().out
    with pytest.raises(SystemExit) as version_exit:
        main(["--version"])
    assert version_exit.value.code == 0
    assert deplens.__version__ in capsys.readouterr().out


def test_updates_non_git_dir(tmp_path, capsys):
    assert main(["updates", str(tmp_path)]) == 2
    assert "error" in capsys.readouterr().err


def test_analyze_missing_path(tmp_path, capsys):
    assert main(["analyze", str(tmp_path / "nope")]) == 2
    assert "no such path" in capsys.readouterr().err
    assert main(["impact", str(tmp_path / "nope"), "--package", "a"]) == 2


def test_analyze_json(tmp_path, capsys):
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    (tmp_path / "app.py").write_text("import requests\nrequests.get('https://x.test')\n")
    assert main(["analyze", str(tmp_path)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["imports"]["count"] == 1
    assert data["usage"]["count"] == 1
    assert data["dependencies"]["nodes"]["requests"]["depth"] == 1


def test_analyze_markdown(tmp_path, capsys):
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    assert main(["analyze", str(tmp_path), "--format", "markdown"]) == 0
    assert "DepLens report" in capsys.readouterr().out


def test_predict_json(capsys):
    assert main(["predict", "--package", "requests", "--old", "1.0.0", "--new", "2.0.0"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["risk_score"] == 60.0
    assert {p["rule"] for p in data["predictions"]} == {
        "major-version",
        "direct-dependency",
        "api-change",
        "dependency-depth",
        "code-usage",
    }


def test_predict_markdown(capsys):
    assert main(["predict", "--package", "a", "--format", "markdown"]) == 0
    assert "Risk score" in capsys.readouterr().out


def test_predict_hybrid_flag(capsys):
    assert main(["predict", "--package", "a", "--hybrid", "--old", "1.0.0", "--new", "2.0.0"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert any(p["rule"] == "hybrid" for p in data["predictions"])


def test_impact_json_and_markdown(tmp_path, capsys):
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    (tmp_path / "app.py").write_text("import requests\nrequests.get('https://x.test')\n")
    assert main(["impact", str(tmp_path), "--package", "requests", "--old", "==2.28.0", "--new", "==2.31.0", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["package"] == "requests"
    assert data["affected_apis"] == ["requests.get"]
    assert str(tmp_path / "app.py") in data["affected_files"]
    assert main(["impact", str(tmp_path), "--package", "requests", "--format", "markdown"]) == 0
    assert "# Impact: requests" in capsys.readouterr().out
