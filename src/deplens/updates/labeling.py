from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from deplens.updates.detection import UpdateRecord, files_changed, list_commits

FIX_RE = re.compile(
    r"\b(revert(?:ed|s|ing)?|downgrade[sd]?|rollback|hotfix|hot-fix|"
    r"fix(?:es|ed|ing)?|broken|breakage|failure|pin(?:ned|ning)?)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UpdateLabel:
    update: UpdateRecord
    label: str
    evidence_commit: str | None = None
    evidence_subject: str | None = None


def label_reverts(records: list[UpdateRecord]) -> dict[int, UpdateRecord]:
    evidence: dict[int, UpdateRecord] = {}
    for i, record in enumerate(records):
        if record.change != "updated" or record.old_constraint is None:
            continue
        for j in range(i - 1, -1, -1):
            later = records[j]
            if (
                later.file == record.file
                and later.package == record.package
                and later.new_constraint == record.old_constraint
            ):
                evidence[i] = later
                break
    return evidence


def label_fix_commits(
    repo: str | Path,
    records: list[UpdateRecord],
    window: int = 10,
) -> dict[int, tuple[str, str]]:
    commits = list_commits(repo)
    position = {sha: idx for idx, (sha, _, _, _) in enumerate(commits)}
    parents = {sha: parent for sha, parent, _, _ in commits}
    changed_cache: dict[str, list[str]] = {}
    evidence: dict[int, tuple[str, str]] = {}
    for i, record in enumerate(records):
        idx = position.get(record.commit)
        if idx is None:
            continue
        for sha, _, _, subject in commits[max(0, idx - window):idx]:
            if sha not in changed_cache:
                changed_cache[sha] = files_changed(repo, sha, parents.get(sha, ""))
            if record.file not in changed_cache[sha]:
                continue
            if FIX_RE.search(subject):
                evidence[i] = (sha, subject)
                break
    return evidence


def label_updates(
    repo: str | Path,
    records: list[UpdateRecord],
    window: int = 10,
) -> list[UpdateLabel]:
    reverts = label_reverts(records)
    fixes = label_fix_commits(repo, records, window)
    labels = []
    for i, record in enumerate(records):
        if i in reverts:
            later = reverts[i]
            labels.append(
                UpdateLabel(record, "reverted", later.commit, later.subject)
            )
        elif i in fixes:
            sha, subject = fixes[i]
            labels.append(UpdateLabel(record, "fix-suspect", sha, subject))
        else:
            labels.append(UpdateLabel(record, "no-signal"))
    return labels
