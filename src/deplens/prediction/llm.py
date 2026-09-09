from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from deplens.prediction.baselines import Prediction, UpdateCase


@dataclass(frozen=True)
class ApiChange:
    name: str
    kind: str
    detail: str = ""


class ApiDiffProvider(Protocol):
    def diff(self, package: str, old_version: str | None, new_version: str | None) -> list[ApiChange]:
        ...


class EmptyApiDiffProvider:
    def diff(self, package: str, old_version: str | None, new_version: str | None) -> list[ApiChange]:
        return []


def removed_apis(changes: list[ApiChange]) -> list[ApiChange]:
    return [change for change in changes if change.kind == "removed"]


def llm_assisted_heuristic(case: UpdateCase, changes: list[ApiChange]) -> Prediction:
    risky = any(change.kind == "removed" for change in changes) or (
        bool(changes) and (case.affected_imports > 0 or case.affected_apis > 0)
    )
    return Prediction(
        package=case.package,
        rule="llm-assisted",
        score=1.0 if risky else 0.0,
        label=risky,
    )
