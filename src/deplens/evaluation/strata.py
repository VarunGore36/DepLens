from __future__ import annotations

from collections.abc import Callable

from deplens.evaluation.metrics import BinaryMetrics
from deplens.evaluation.scoring import score_rules
from deplens.prediction.baselines import UpdateCase, semver_change


def directness_stratum(case: UpdateCase) -> str:
    return "direct" if case.direct else "transitive"


def semver_stratum(case: UpdateCase) -> str:
    change = semver_change(case.old_version, case.new_version)
    return "major" if change == "major" else "non-major"


def score_by_stratum(
    cases: list[UpdateCase],
    labels: list[bool],
    stratify: Callable[[UpdateCase], str] = directness_stratum,
) -> dict[str, dict[str, BinaryMetrics]]:
    if len(cases) != len(labels):
        raise ValueError(f"length mismatch: {len(cases)} cases vs {len(labels)} labels")
    groups: dict[str, tuple[list[UpdateCase], list[bool]]] = {}
    for case, label in zip(cases, labels):
        key = stratify(case)
        pair = groups.setdefault(key, ([], []))
        pair[0].append(case)
        pair[1].append(label)
    return {
        stratum: score_rules(group_cases, group_labels)
        for stratum, (group_cases, group_labels) in sorted(groups.items())
    }
