from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

MARKER = "<!-- deplens-report -->"


def build_comment_body(report: str) -> str:
    return f"{MARKER}\n{report.rstrip()}\n\n_DepLens scores are unevaluated heuristics, not predictions._"


def _api(path: str, token: str, data: dict | None = None, method: str = "GET") -> dict:
    request = urllib.request.Request(
        f"https://api.github.com{path}",
        data=json.dumps(data).encode() if data is not None else None,
        method=method if data is not None else "GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def post_comment(report_path: str) -> int:
    token = os.environ.get("GH_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    pr_number = os.environ.get("PR_NUMBER") or os.environ.get("GITHUB_REF", "").rsplit("/", 1)[-1]
    if not token or not repo or not pr_number:
        print("missing GH_TOKEN, GITHUB_REPOSITORY, or PR number", file=sys.stderr)
        return 1
    body = build_comment_body(Path(report_path).read_text(encoding="utf-8"))
    comments = _api(f"/repos/{repo}/issues/{pr_number}/comments", token)
    existing = next((c for c in comments if MARKER in c.get("body", "")), None)
    if existing:
        _api(f"/repos/{repo}/issues/comments/{existing['id']}", token, {"body": body}, "PATCH")
    else:
        _api(f"/repos/{repo}/issues/{pr_number}/comments", token, {"body": body})
    return 0


if __name__ == "__main__":
    sys.exit(post_comment(sys.argv[1]))
