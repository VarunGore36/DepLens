from __future__ import annotations

import argparse
import json
import sys

from deplens.prediction.baselines import UpdateCase, run_baselines
from deplens.prediction.hybrid import HybridWeights, hybrid_predict
from deplens.report import analysis_markdown, predictions_markdown, risk_score, to_json


def _analyze(args: argparse.Namespace) -> int:
    from pathlib import Path

    from deplens.project import analyze_project

    if not Path(args.path).exists():
        print(f"error: no such path: {args.path}", file=sys.stderr)
        return 2
    analysis = analyze_project(args.path)
    if args.format == "markdown":
        print(analysis_markdown(analysis))
    else:
        print(to_json(analysis))
    return 0


def _predict(args: argparse.Namespace) -> int:
    case = UpdateCase(
        package=args.package,
        old_version=args.old,
        new_version=args.new,
        direct=not args.transitive,
        depth=args.depth,
        api_changed=args.api_changed,
        affected_imports=args.affected_imports,
        affected_apis=args.affected_apis,
    )
    predictions = run_baselines(case)
    if args.hybrid:
        predictions = [*predictions, hybrid_predict(case, HybridWeights())]
    payload = {
        "package": case.package,
        "risk_score": risk_score(predictions),
        "predictions": [
            {"rule": p.rule, "score": p.score, "label": p.label} for p in predictions
        ],
    }
    if args.format == "markdown":
        print(predictions_markdown(predictions))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _updates(args: argparse.Namespace) -> int:
    from deplens.updates import detect_updates, label_updates

    records = detect_updates(args.repo, args.limit)
    labels = label_updates(args.repo, records)
    payload = [
        {
            "commit": record.commit,
            "package": record.package,
            "change": record.change,
            "old": record.old_constraint,
            "new": record.new_constraint,
            "label": label.label,
            "evidence": label.evidence_commit,
        }
        for record, label in zip(records, labels)
    ]
    print(json.dumps(payload, indent=2))
    return 0


def _impact(args: argparse.Namespace) -> int:
    from pathlib import Path

    from deplens.project import analyze_project

    if not Path(args.path).exists():
        print(f"error: no such path: {args.path}", file=sys.stderr)
        return 2
    analysis = analyze_project(args.path, include_objects=True)
    objects = analysis["objects"]
    from deplens.prediction.impact import build_impact, impact_json, impact_markdown

    report = build_impact(
        args.package, args.old, args.new, objects["graph"], objects["links"], objects["usages"]
    )
    if args.format == "markdown":
        print(impact_markdown(report))
    else:
        print(json.dumps(impact_json(report), indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deplens", description="Dependency impact research tool")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="Analyze a project directory")
    analyze.add_argument("path", help="Project directory")
    analyze.add_argument("--format", choices=["json", "markdown"], default="json")
    analyze.set_defaults(func=_analyze)

    predict = sub.add_parser("predict", help="Score one dependency update")
    predict.add_argument("--package", required=True)
    predict.add_argument("--old", default=None)
    predict.add_argument("--new", default=None)
    predict.add_argument("--depth", type=int, default=None)
    predict.add_argument("--transitive", action="store_true")
    predict.add_argument("--api-changed", action="store_true")
    predict.add_argument("--affected-imports", type=int, default=0)
    predict.add_argument("--affected-apis", type=int, default=0)
    predict.add_argument("--hybrid", action="store_true")
    predict.add_argument("--format", choices=["json", "markdown"], default="json")
    predict.set_defaults(func=_predict)

    updates = sub.add_parser("updates", help="List labeled dependency updates in a repo")
    updates.add_argument("repo", help="Git repository path")
    updates.add_argument("--limit", type=int, default=None)
    updates.set_defaults(func=_updates)

    impact = sub.add_parser("impact", help="Impact report for one update in a project")
    impact.add_argument("path", help="Project directory")
    impact.add_argument("--package", required=True)
    impact.add_argument("--old", default=None)
    impact.add_argument("--new", default=None)
    impact.add_argument("--format", choices=["json", "markdown"], default="markdown")
    impact.set_defaults(func=_impact)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
