import pytest

from deplens.dependencies import parse_requirements_text


def test_basic_requirements():
    parsed = parse_requirements_text("requests>=2.0,<3\nnumpy==1.26.0\n")
    assert parsed.names() == ["requests", "numpy"]
    by_name = parsed.by_name()
    assert set(by_name["requests"][0].constraint.split(",")) == {">=2.0", "<3"}
    assert by_name["numpy"][0].constraint == "==1.26.0"


def test_comments_options_and_markers():
    text = "# comment\nrequests[security]>=2.0; python_version > '3.8'  # inline\n-r other.txt\n--index-url https://example.com\n\nDjango==4.2\n"
    parsed = parse_requirements_text(text)
    assert parsed.names() == ["requests", "django"]
    req = parsed.by_name()["requests"][0]
    assert req.extras == ("security",)
    assert req.marker is not None and "python_version" in req.marker


def test_name_canonicalization():
    parsed = parse_requirements_text("Pillow>=10\npillow<11\n")
    assert parsed.names() == ["pillow"]
    assert len(parsed.by_name()["pillow"]) == 2


def test_invalid_requirement_raises():
    with pytest.raises(ValueError, match="invalid requirement"):
        parse_requirements_text("!!!not-valid!!!\n")
