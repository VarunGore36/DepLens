import json

from deplens.cli import main


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
