from __future__ import annotations

from dataclasses import dataclass, field

from packaging.utils import canonicalize_name

from deplens.analysis.linking import ImportLink, affected_imports
from deplens.analysis.usage import UsageRecord, usages_for_dependency
from deplens.graph.model import DependencyGraph
from deplens.prediction.baselines import Prediction, UpdateCase, run_baselines
from deplens.prediction.cases import build_case
from deplens.report import risk_band, risk_score


@dataclass(frozen=True)
class ImpactReport:
    package: str
    old_constraint: str | None
    new_constraint: str | None
    direct: bool
    depth: int | None
    affected_files: list[str] = field(default_factory=list)
    affected_apis: list[str] = field(default_factory=list)
    predictions: list[Prediction] = field(default_factory=list)
    risk: float = 0.0
    band: str = "low"


def build_impact(
    package: str,
    old_constraint: str | None,
    new_constraint: str | None,
    graph: DependencyGraph,
    links: list[ImportLink] | None = None,
    usages: list[UsageRecord] | None = None,
    api_changed: bool | None = None,
) -> ImpactReport:
    key = canonicalize_name(package)
    case = build_case(package, old_constraint, new_constraint, graph, links, usages, api_changed)
    return impact_from_case(key, old_constraint, new_constraint, case, links, usages)


def impact_from_case(
    package: str,
    old_constraint: str | None,
    new_constraint: str | None,
    case: UpdateCase,
    links: list[ImportLink] | None = None,
    usages: list[UsageRecord] | None = None,
) -> ImpactReport:
    key = canonicalize_name(package)
    files = sorted(
        {
            link.record.source
            for link in affected_imports(links or [], key)
            if link.record.source
        }
    )
    apis = sorted({u.qualified for u in usages_for_dependency(usages or [], key)})
    predictions = run_baselines(case)
    score = risk_score(predictions)
    return ImpactReport(
        package=key,
        old_constraint=old_constraint,
        new_constraint=new_constraint,
        direct=case.direct,
        depth=case.depth,
        affected_files=files,
        affected_apis=apis,
        predictions=predictions,
        risk=score,
        band=risk_band(score),
    )


def impact_markdown(report: ImpactReport) -> str:
    lines = [
        f"# Impact: {report.package} ({report.old_constraint or '?'} → {report.new_constraint or '?'})",
        "",
        (
            f"Risk: {report.risk:.0f}/100 ({report.band}) — "
            f"{'direct' if report.direct else 'transitive'}, depth {report.depth}"
        ),
        "",
        "## Affected files",
        "",
    ]
    lines += [f"- {path}" for path in report.affected_files] or ["- none traced"]
    lines += ["", "## Affected APIs (all used APIs: removal/change status unknown)", ""]
    lines += [f"- {api}" for api in report.affected_apis] or ["- none traced"]
    lines += ["", "## Rule verdicts", ""]
    for prediction in report.predictions:
        lines.append(f"- {prediction.rule}: {'risky' if prediction.label else 'clear'}")
    lines += ["", "_Potentially-affected sets are conservative over-approximations: DepLens traces what the repo uses, not what the new version changed._"]
    return "\n".join(lines)


def impact_json(report: ImpactReport) -> dict:
    return {
        "package": report.package,
        "old_constraint": report.old_constraint,
        "new_constraint": report.new_constraint,
        "direct": report.direct,
        "depth": report.depth,
        "affected_files": report.affected_files,
        "affected_apis": report.affected_apis,
        "risk": report.risk,
        "band": report.band,
        "predictions": [
            {"rule": p.rule, "score": p.score, "label": p.label} for p in report.predictions
        ],
    }
