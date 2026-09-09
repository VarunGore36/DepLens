from deplens.analysis import collect_usage, parse_usage_text, usages_for_dependency


def test_from_import_call():
    parsed = parse_usage_text("from requests import get\nresp = get('https://example.com')\n")
    assert [(u.qualified, u.is_call) for u in parsed.usages] == [("requests.get", True)]


def test_import_alias_attribute_call():
    parsed = parse_usage_text("import numpy as np\nnp.array([1])\n")
    assert [(u.qualified, u.is_call) for u in parsed.usages] == [("numpy.array", True)]


def test_submodule_import():
    parsed = parse_usage_text("import os.path\nos.path.join('a', 'b')\n")
    assert [u.qualified for u in parsed.usages] == ["os.path.join"]


def test_unrelated_names_ignored():
    parsed = parse_usage_text("import requests\nx = 1\ny = x + 1\n")
    assert parsed.usages == []


def test_usages_for_dependency_with_alias():
    parsed = parse_usage_text("from PIL import Image\nImage.open('x.png')\n")
    assert [u.qualified for u in usages_for_dependency(parsed.usages, "pillow")] == [
        "PIL.Image.open",
    ]


def test_collect_usage(tmp_path):
    (tmp_path / "a.py").write_text("import requests\nrequests.get('https://example.com')\n")
    collected = collect_usage(tmp_path)
    assert collected.files_scanned == 1
    assert [u.qualified for u in collected.usages] == ["requests.get"]
