import pytest

from deplens.dependencies import (
    parse_lockfile_file,
    parse_pipfile_lock_text,
    parse_poetry_lock_text,
    parse_uv_lock_text,
)


def test_poetry_lock():
    text = '[[package]]\nname = "requests"\nversion = "2.31.0"\n\n[[package]]\nname = "urllib3"\nversion = "2.0.7"\n'
    parsed = parse_poetry_lock_text(text)
    assert parsed.names() == ["requests", "urllib3"]
    assert parsed.by_name()["requests"][0].constraint == "==2.31.0"


def test_uv_lock():
    text = '[[package]]\nname = "numpy"\nversion = "1.26.4"\n'
    parsed = parse_uv_lock_text(text)
    assert parsed.by_name()["numpy"][0].constraint == "==1.26.4"


def test_pipfile_lock():
    text = '{"default": {"requests": {"version": "==2.31.0"}}, "develop": {"pytest": {"version": "==8.0.0"}}}'
    parsed = parse_pipfile_lock_text(text)
    assert parsed.names() == ["requests", "pytest"]


def test_invalid_pipfile_lock_raises():
    with pytest.raises(ValueError, match="invalid JSON"):
        parse_pipfile_lock_text("{broken")


def test_lockfile_dispatch(tmp_path):
    poetry = tmp_path / "poetry.lock"
    poetry.write_text('[[package]]\nname = "requests"\nversion = "2.31.0"\n')
    assert parse_lockfile_file(poetry).names() == ["requests"]
    pipfile = tmp_path / "Pipfile.lock"
    pipfile.write_text('{"default": {"flask": {"version": "==3.0.0"}}}')
    assert parse_lockfile_file(pipfile).names() == ["flask"]
    req_lock = tmp_path / "requirements-prod.lock"
    req_lock.write_text("django==4.2\n")
    assert parse_lockfile_file(req_lock).names() == ["django"]
