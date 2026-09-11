from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import deplens
from deplens.evaluation import ablate, score_rules
from deplens.graph import DependencyGraph
from deplens.prediction import build_case, run_baselines
from deplens.project import analyze_project
from deplens.updates import (
    detect_updates,
    export_tree,
    label_test_outcomes,
    label_test_outcomes_isolated,
)

DECIDABLE = {"breaks-tests": True, "passes": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="DepLens test-grounded evaluation")
    parser.add_argument("--repo", action="append", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--file", action="append", default=None)
    parser.add_argument("--cmd", nargs="*", default=None)
    parser.add_argument("--prepend-src", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--isolate", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--install-timeout", type=int, default=600)
    parser.add_argument("--deselect", action="append", default=[])
    args = parser.parse_args()
    deselect_args = [flag for node in args.deselect for flag in ("--deselect", node)]
    cmd = (args.cmd or [sys.executable, "-m", "pytest", "-q"]) + deselect_args
    isolated_args = ["-m", "pytest", "-q", *deselect_args]
    if args.cmd is None and not args.isolate:
        probe = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode != 0:
            print("pytest is not importable from this interpreter.", file=sys.stderr)
            print("hint: invoke with 'uv run --with pytest python scripts/evaluate_test_outcomes.py ...'", file=sys.stderr)
            return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cases: list = []
    labels: list = []
    rows: list = []
    distribution: dict = {}
    for repo in args.repo:
        records = detect_updates(repo)
        if args.file:
            records = [r for r in records if any(f in r.file for f in args.file)]
        if args.isolate:
            outcomes = label_test_outcomes_isolated(
                repo, records, isolated_args,
                args.timeout, args.install_timeout, limit=args.limit, undecidable_codes=(5,),
            )
        else:
            outcomes = label_test_outcomes(
                repo, records, cmd, args.timeout, limit=args.limit, prepend_src=args.prepend_src,
                undecidable_codes=(5,),
            )
        for record, outcome in zip(records, outcomes):
            distribution[outcome.label] = distribution.get(outcome.label, 0) + 1
            if outcome.label not in DECIDABLE:
                continue
            with tempfile.TemporaryDirectory(prefix="deplens-") as tmp:
                if record.parent and export_tree(repo, record.parent, Path(tmp)):
                    analysis = analyze_project(tmp, include_objects=True)
                    objects = analysis["objects"]
                    case = build_case(
                        record.package,
                        record.old_constraint,
                        record.new_constraint,
                        objects["graph"],
                        objects["links"],
                        objects["usages"],
                    )
                else:
                    case = build_case(
                        record.package, record.old_constraint, record.new_constraint, DependencyGraph()
                    )
            weak = DECIDABLE[outcome.label]
            cases.append(case)
            labels.append(weak)
            rows.append(
                {
                    "repo": repo,
                    "commit": record.commit,
                    "package": case.package,
                    "change": record.change,
                    "test_label": outcome.label,
                    "weak_label": weak,
                    "features": {
                        "direct": case.direct,
                        "depth": case.depth,
                        "affected_imports": case.affected_imports,
                        "affected_apis": case.affected_apis,
                    },
                    "predictions": {p.rule: p.label for p in run_baselines(case)},
                }
            )

    scores = score_rules(cases, labels) if cases else {}
    ablation = ablate(cases, labels) if cases else None
    metrics = {
        "n_decidable": len(cases),
        "n_positive_test": sum(labels),
        "outcome_distribution": distribution,
        "rules": {rule: dataclasses.asdict(m) for rule, m in scores.items()},
        "ablation_delta_f1": ablation.delta_f1 if ablation else None,
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (out / "cases.jsonl").write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows))
    (out / "config.yaml").write_text(
        f"experiment: test-grounded\n"
        f"date: {datetime.datetime.now(datetime.timezone.utc).date().isoformat()}\n"
        f"deplens: {deplens.__version__}\n"
        f"repos: {json.dumps(args.repo)}\n"
        f"cmd: {json.dumps(cmd)}\n"
        f"timeout: {args.timeout}\n"
        f"isolate: {args.isolate}\n"
        f"deselect: {json.dumps(args.deselect)}\n"
        f"labels: test-grounded (breaks-tests -> true, passes -> false; others dropped)\n"
    )
    table = "".join(
        f"| {rule} | {m.precision:.2f} | {m.recall:.2f} | {m.f1:.2f} |\n"
        for rule, m in scores.items()
    )
    readme = (
        "# Test-grounded evaluation\n\n"
        f"Decidable cases: {len(cases)} ({sum(labels)} breaking). "
        f"Outcome distribution: {json.dumps(distribution, sort_keys=True)}. "
        "Dropped outcomes (already-failing, no-tests, error, timeout) are not evidence for or against "
        "any rule and are excluded from scoring.\n\n"
        "## Per-rule metrics\n\n"
        "| Rule | Precision | Recall | F1 |\n| --- | --- | --- | --- |\n" + table
    )
    (out / "README.md").write_text(readme)
    print(readme)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
