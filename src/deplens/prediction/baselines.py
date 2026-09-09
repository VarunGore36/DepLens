from __future__ import annotations

from dataclasses import dataclass

from packaging.version import InvalidVersion, Version


@dataclass(frozen=True)
class UpdateCase:
    package: str
    old_version: str | None = None
    new_version: str | None = None
    direct: bool = True
    depth: int | None = None
    api_changed: bool | None = None
    affected_imports: int = 0
    affected_apis: int = 0


@dataclass(frozen=True)
class Prediction:
    package: str
    rule: str
    score: float
    label: bool


def coerce_version(constraint: str | None) -> str | None:
    if not constraint:
        return None
    text = constraint.strip()
    if text.startswith("=="):
        text = text[2:].strip()
    try:
        return str(Version(text))
    except InvalidVersion:
        return None


def semver_change(old: str | None, new: str | None) -> str:
    try:
        old_v = Version(old) if old else None
        new_v = Version(new) if new else None
    except InvalidVersion:
        return "unknown"
    if old_v is None or new_v is None:
        return "unknown"
    if new_v.major != old_v.major:
        return "major"
    if new_v.minor != old_v.minor:
        return "minor"
    if new_v.micro != old_v.micro:
        return "patch"
    return "other"


def _decide(rule: str, package: str, risky: bool) -> Prediction:
    return Prediction(package=package, rule=rule, score=1.0 if risky else 0.0, label=risky)


def major_version_heuristic(case: UpdateCase) -> Prediction:
    return _decide(
        "major-version",
        case.package,
        semver_change(case.old_version, case.new_version) == "major",
    )


def direct_dependency_heuristic(case: UpdateCase) -> Prediction:
    return _decide("direct-dependency", case.package, case.direct)


def api_change_heuristic(case: UpdateCase) -> Prediction:
    return _decide("api-change", case.package, case.api_changed is True)


def depth_heuristic(case: UpdateCase, threshold: int = 2) -> Prediction:
    return _decide(
        "dependency-depth",
        case.package,
        case.depth is None or case.depth >= threshold,
    )


def usage_heuristic(case: UpdateCase) -> Prediction:
    return _decide(
        "code-usage",
        case.package,
        case.affected_imports > 0 or case.affected_apis > 0,
    )


BASELINES = {
    "major-version": major_version_heuristic,
    "direct-dependency": direct_dependency_heuristic,
    "api-change": api_change_heuristic,
    "dependency-depth": depth_heuristic,
    "code-usage": usage_heuristic,
}


def run_baselines(case: UpdateCase) -> list[Prediction]:
    return [fn(case) for fn in BASELINES.values()]
