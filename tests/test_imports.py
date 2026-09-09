import pytest

from deplens.analysis import (
    affected_imports,
    collect_imports,
    link_imports,
    parse_imports_text,
)


def test_parse_import_statements():
    parsed = parse_imports_text("import os\nimport requests\nfrom numpy import array\n")
    assert [r.top_level() for r in parsed.records] == ["os", "requests", "numpy"]
    assert parsed.top_levels() == ["os", "requests", "numpy"]


def test_relative_import_without_module():
    parsed = parse_imports_text("from . import helper\n")
    assert parsed.records[0].top_level() == ""
    assert parsed.records[0].level == 1


def test_invalid_python_raises():
    with pytest.raises(ValueError, match="invalid Python"):
        parse_imports_text("def broken(:\n")


def test_collect_imports_skips_venv(tmp_path):
    (tmp_path / "app.py").write_text("import requests\n")
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "ignored.py").write_text("import definitely_not_used_xyz\n")
    collected = collect_imports(tmp_path)
    assert collected.files_scanned == 1
    assert collected.top_levels() == ["requests"]


def test_linking_exact_alias_and_stdlib():
    parsed = parse_imports_text("import os\nimport requests\nfrom PIL import Image\nimport no_such_pkg_xyz\n")
    links = link_imports(parsed.records, ["requests", "pillow"])
    by_module = {link.record.top_level(): link for link in links}
    assert by_module["os"].stdlib is True
    assert by_module["os"].dependency is None
    assert by_module["requests"].dependency == "requests"
    assert by_module["PIL"].dependency == "pillow"
    assert by_module["no_such_pkg_xyz"].dependency is None
    assert [link.record.top_level() for link in affected_imports(links, "pillow")] == ["PIL"]
