from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import deplens
from deplens.prediction.baselines import UpdateCase, run_baselines
from deplens.prediction.hybrid import HybridWeights, hybrid_predict
from deplens.report import analysis_markdown, predictions_markdown, risk_score, to_json

DISCLAIMER = "Scores are unevaluated heuristics, not predictions."
RECENT_LIMIT = 50
FULL_LIMIT = 200


def _analyze(args: argparse.Namespace) -> int:
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

    try:
        records = detect_updates(args.repo, args.limit)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
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


def _checked_path(path: str) -> Path | None:
    candidate = Path(path)
    if not candidate.exists():
        print(f"error: no such path: {path}", file=sys.stderr)
        return None
    return candidate


def _load_analysis(path: str) -> dict | None:
    from deplens.project import analyze_project

    if _checked_path(path) is None:
        return None
    return analyze_project(path, include_objects=True)


def _recent_updates(path: str, limit: int) -> tuple[list, list, str | None]:
    from deplens.updates import detect_updates, label_updates

    try:
        records = detect_updates(path, limit)
    except ValueError:
        return [], [], "not a git repository: update history skipped"
    return records, label_updates(path, records), None


def _impacts_for_updates(analysis: dict, records: list) -> list[dict]:
    from deplens.prediction.impact import build_impact, impact_json

    objects = analysis["objects"]
    impacts = []
    for record in records:
        report = build_impact(
            record.package,
            record.old_constraint,
            record.new_constraint,
            objects["graph"],
            objects["links"],
            objects["usages"],
        )
        payload = impact_json(report)
        payload["commit"] = record.commit
        impacts.append(payload)
    return impacts


def _summarize(analysis: dict, records: list, impacts: list) -> list[str]:
    deps = analysis["dependencies"]
    direct = len(deps["edges"].get(deps["root"], []))
    imports = analysis["imports"]
    usage = analysis["usage"]
    lines = [
        f"Repository: {analysis['root']}",
        "",
        (
            f"Dependencies: {len(deps['nodes'])} packages ({direct} direct)"
            f" from {len(analysis['dependency_files'])} file(s)"
        ),
        (
            f"Code usage: {imports['count']} imports "
            f"({imports['linked']} linked, {imports['stdlib']} stdlib, "
            f"{imports['unresolved']} unresolved); {len(usage['qualified'])} distinct APIs"
        ),
    ]
    if records:
        lines.append(f"Recent updates: {len(records)}")
        for record, impact in zip(records, impacts):
            lines.append(
                f"  - {record.package} ({record.change}): "
                f"risk {impact['risk']:.0f}/100 ({impact['band']}), "
                f"{len(impact['affected_files'])} file(s), "
                f"{len(impact['affected_apis'])} API(s)"
            )
    else:
        lines.append("Recent updates: none found")
    flagged = sum(1 for impact in impacts if impact["band"] in ("medium", "high"))
    lines += ["", f"Flagged updates: {flagged}", f"_{DISCLAIMER}_"]
    return lines


def _pipeline_payload(analysis: dict, records: list, labels: list, impacts: list) -> dict:
    return {
        "root": analysis["root"],
        "dependency_files": analysis["dependency_files"],
        "parse_errors": analysis["parse_errors"],
        "dependencies": analysis["dependencies"],
        "node_features": analysis["node_features"],
        "imports": analysis["imports"],
        "usage": analysis["usage"],
        "updates": [
            {
                "commit": record.commit,
                "package": record.package,
                "change": record.change,
                "old": record.old_constraint,
                "new": record.new_constraint,
                "label": label.label,
            }
            for record, label in zip(records, labels)
        ],
        "impacts": impacts,
    }


def _emit(text: str, output: str | None) -> int:
    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
        print(f"Report written to {output}")
        return 0
    print(text)
    return 0


def _run_pipeline(args: argparse.Namespace, limit: int, history: bool) -> int:
    analysis = _load_analysis(args.path)
    if analysis is None:
        return 2
    records, labels, note = ([], [], None)
    if history:
        records, labels, note = _recent_updates(args.path, limit)
    impacts = _impacts_for_updates(analysis, records)
    if args.format == "json":
        return _emit(to_json(_pipeline_payload(analysis, records, labels, impacts)), args.output)
    if args.format == "markdown":
        return _emit(analysis_markdown(analysis), args.output)
    lines = [f"DepLens — {args.command or 'default'}", ""]
    lines += _summarize(analysis, records, impacts)
    if note:
        lines += ["", f"Note: {note}."]
    if analysis["parse_errors"]:
        lines += ["", f"Parse errors: {len(analysis['parse_errors'])} (see JSON output)."]
    return _emit("\n".join(lines), args.output)


def _default(args: argparse.Namespace) -> int:
    return _run_pipeline(args, RECENT_LIMIT, history=True)


def _quick(args: argparse.Namespace) -> int:
    return _run_pipeline(args, 0, history=False)


def _full(args: argparse.Namespace) -> int:
    return _run_pipeline(args, FULL_LIMIT, history=True)


def _dependencies(args: argparse.Namespace) -> int:
    analysis = _load_analysis(args.path)
    if analysis is None:
        return 2
    deps = analysis["dependencies"]
    if args.format == "json":
        return _emit(
            to_json(
                {
                    "root": analysis["root"],
                    "dependency_files": analysis["dependency_files"],
                    "dependencies": deps,
                    "node_features": analysis["node_features"],
                }
            ),
            args.output,
        )
    if args.format == "markdown":
        lines = [f"# Dependencies: {analysis['root']}", ""]
    else:
        lines = [f"DepLens dependencies — {analysis['root']}", ""]
    for name in sorted(deps["nodes"]):
        node = deps["nodes"][name]
        constraint = node["constraints"][0] if node["constraints"] else "unpinned"
        kind = "direct" if node["direct"] else f"depth {node['depth']}"
        lines.append(f"- {name} {constraint} ({kind})")
    if not deps["nodes"]:
        lines.append("(no dependencies found)")
    return _emit("\n".join(lines), args.output)


def _usage(args: argparse.Namespace) -> int:
    analysis = _load_analysis(args.path)
    if analysis is None:
        return 2
    imports = analysis["imports"]
    usage = analysis["usage"]
    if args.format == "json":
        return _emit(
            to_json({"root": analysis["root"], "imports": imports, "usage": usage}),
            args.output,
        )
    if args.format == "markdown":
        lines = [f"# Code usage: {analysis['root']}", ""]
    else:
        lines = [f"DepLens usage — {analysis['root']}", ""]
    lines += [
        (
            f"Imports: {imports['count']} "
            f"({imports['linked']} linked, {imports['stdlib']} stdlib, "
            f"{imports['unresolved']} unresolved)"
        ),
        "",
        "Top-level modules:",
    ]
    lines += [f"- {name}" for name in imports["top_levels"][:20]] or ["(none)"]
    lines += ["", f"Distinct APIs used: {len(usage['qualified'])}"]
    return _emit("\n".join(lines), args.output)


def _add_common(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("path", nargs="?", default=".")
    subparser.add_argument("--format", choices=["human", "json", "markdown"], default="human")
    subparser.add_argument("--output", default=None, help="Write report to FILE as well")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deplens",
        description="Understand dependency/update impact of a repository.",
        epilog=(
            "examples:\n"
            "  deplens                    analyze the current directory\n"
            "  deplens .                  same, explicit path\n"
            "  deplens quick              fast analysis (no history mining)\n"
            "  deplens full               exhaustive analysis with update impacts\n"
            "  deplens impact . --package requests --new '==2.31.0'\n"
            "  deplens --format json > report.json   machine-readable output"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {deplens.__version__}")
    parser.add_argument("--format", choices=["human", "json", "markdown"], default="human")
    parser.add_argument("--output", default=None, help="Write report to FILE")
    parser.set_defaults(func=_default, command=None)
    sub = parser.add_subparsers(dest="command")

    quick = sub.add_parser("quick", help="Fast analysis of a repository (no history mining)")
    _add_common(quick)
    quick.set_defaults(func=_quick)

    full = sub.add_parser("full", help="Exhaustive analysis with update impacts")
    _add_common(full)
    full.set_defaults(func=_full)

    dependencies = sub.add_parser("dependencies", help="Show dependency inventory of a repository")
    _add_common(dependencies)
    dependencies.set_defaults(func=_dependencies)

    usage = sub.add_parser("usage", help="Show code-usage summary of a repository")
    _add_common(usage)
    usage.set_defaults(func=_usage)

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


_SUBCOMMANDS = {"quick", "full", "dependencies", "usage", "analyze", "predict", "updates", "impact"}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    raw = sys.argv[1:] if argv is None else list(argv)
    default_path = "."
    first_bare = next((a for a in raw if not a.startswith("-")), None)
    if first_bare is not None and first_bare not in _SUBCOMMANDS:
        default_path = first_bare
        raw = raw[: raw.index(first_bare)] + raw[raw.index(first_bare) + 1 :]
    args = parser.parse_args(raw)
    if args.command is None:
        args.path = default_path
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
