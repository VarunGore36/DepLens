import pytest

from deplens.dependencies import parse_pyproject_text


def test_pep621_and_optional():
    text = """
[project]
name = "demo"
dependencies = ["requests>=2", "numpy==1.26.0"]
[project.optional-dependencies]
test = ["pytest>=8"]
"""
    parsed = parse_pyproject_text(text)
    assert parsed.names() == ["requests", "numpy", "pytest"]
    assert parsed.by_name()["pytest"][0].source == "pyproject.toml:project.optional-dependencies[test]"


def test_poetry_main_and_groups():
    text = """
[tool.poetry.dependencies]
python = "^3.10"
requests = "^2.28"
flask = { version = ">=2", extras = ["async"], markers = "python_version >= '3.8'" }

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
"""
    parsed = parse_pyproject_text(text)
    assert parsed.names() == ["requests", "flask", "pytest"]
    flask = parsed.by_name()["flask"][0]
    assert flask.extras == ("async",)
    assert flask.marker is not None


def test_invalid_toml_raises():
    with pytest.raises(ValueError, match="invalid TOML"):
        parse_pyproject_text("[project\nbroken = ")
