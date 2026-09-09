from deplens.prediction import Prediction
from deplens.project import analyze_project, discover_dependency_files
from deplens.report import analysis_markdown, risk_band, risk_score


def test_discover_and_analyze(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    (tmp_path / "app.py").write_text("import os\n")
    assert discover_dependency_files(tmp_path) == [tmp_path / "requirements.txt"]
    analysis = analyze_project(tmp_path)
    assert analysis["parse_errors"] == []
    assert analysis["imports"]["stdlib"] == 1
    assert analysis["usage"]["count"] == 0


def test_analyze_records_parse_errors(tmp_path):
    (tmp_path / "requirements.txt").write_text("!!!not-valid!!!\n")
    analysis = analyze_project(tmp_path)
    assert len(analysis["parse_errors"]) == 1
    assert analysis["dependencies"]["nodes"] == {}


def test_risk_score_and_bands():
    predictions = [
        Prediction("a", "r1", 1.0, True),
        Prediction("a", "r2", 0.0, False),
        Prediction("a", "r3", 0.5, True),
    ]
    assert risk_score(predictions) == 50.0
    assert risk_score([]) == 0.0
    assert risk_band(0) == "low"
    assert risk_band(50) == "medium"
    assert risk_band(90) == "high"


def test_analysis_markdown_sections(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    text = analysis_markdown(analyze_project(tmp_path))
    assert "## Dependencies" in text and "## Code usage" in text
    assert "unevaluated heuristics" in text
