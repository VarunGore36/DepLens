import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "post_pr_comment", Path(__file__).parent.parent / "scripts" / "post_pr_comment.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_comment_body_marks_and_disclaims():
    body = module.build_comment_body("# Report\n")
    assert "<!-- deplens-report -->" in body
    assert "unevaluated heuristics" in body
