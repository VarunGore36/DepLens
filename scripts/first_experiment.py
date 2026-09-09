from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path

import deplens
from deplens.evaluation import ablate, score_rules
from deplens.graph import DependencyGraph
from deplens.prediction import build_case, run_baselines
from deplens.project import analyze_project
from deplens.updates import detect_updates, label_updates

WEAK_POSITIVE = ("reverted", "fix-suspect")


def export_parent(repo: str, commit: str, dest: Path) -> bool:
    archive = subprocess.run(
        ["git", "-C", repo, "archive", commit],
        capture_output=True,
    )
    if archive.returncode != 0:
        return False
    with tempfile.NamedTemporaryFile(suffix=".tar") as tmp:
        tmp.write(archive.stdout)
        tmp.flush()
        with tarfile.open(tmp.name) as tar:
            tar.extractall(dest, filter="data")
    return True


def run_repo(repo: str, max_updates: int) -> dict:
    records = detect_updates(repo)[:max_updates]
    labels = label_updates(repo, records)
    cases = []
    rows = []
    for record, label in zip(records, labels):
        weak = label.label in WEAK_POSITIVE
        with tempfile.TemporaryDirectory(prefix="deplens-") as tmp:
            if record.parent and export_parent(repo, record.parent, Path(tmp)):
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
        cases.append((case, weak))
        rows.append(
            {
                "repo": repo,
                "commit": record.commit,
                "package": case.package,
                "change": record.change,
                "old": record.old_constraint,
                "new": record.new_constraint,
                "features": {
                    "old_version": case.old_version,
                    "new_version": case.new_version,
                    "direct": case.direct,
                    "depth": case.depth,
                    "affected_imports": case.affected_imports,
                    "affected_apis": case.affected_apis,
                },
                "heuristic_label": label.label,
                "weak_label": weak,
                "predictions": {p.rule: p.label for p in run_baselines(case)},
            }
        )
    return {"records": records, "cases": cases, "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="DepLens first real-data experiment")
    parser.add_argument("--repo", action="append", required=True)
    parser.add_argument("--max-updates", type=int, default=20)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    all_cases, all_labels, all_rows = [], [], []
    for repo in args.repo:
        result = run_repo(repo, args.max_updates)
        all_cases.extend(c for c, _ in result["cases"])
        all_labels.extend(w for _, w in result["cases"])
        all_rows.extend(result["rows"])

    scores = score_rules(all_cases, all_labels)
    ablation = ablate(all_cases, all_labels)
    metrics = {
        "n_cases": len(all_cases),
        "n_positive_weak": sum(all_labels),
        "rules": {rule: dataclasses.asdict(m) for rule, m in scores.items()},
        "ablation": {
            "metadata_best_rule": ablation.metadata_best_rule,
            "metadata_f1": ablation.metadata_f1,
            "usage_best_rule": ablation.usage_best_rule,
            "usage_f1": ablation.usage_f1,
            "delta_f1": ablation.delta_f1,
            "delta_precision": ablation.delta_precision,
            "delta_recall": ablation.delta_recall,
        },
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (out / "cases.jsonl").write_text("\n".join(json.dumps(r, sort_keys=True) for r in all_rows))
    config = (
        f"experiment: first-run\n"
        f"date: {datetime.date.today().isoformat()}\n"
        f"deplens: {deplens.__version__}\n"
        f"repos: {json.dumps(args.repo)}\n"
        f"max_updates_per_repo: {args.max_updates}\n"
        f"features: pre-update parent commit via git archive\n"
        f"labels: weak heuristic mapping (reverted/fix-suspect -> true, no-signal -> false)\n"
    )
    (out / "config.yaml").write_text(config)
    readme = (
        "# First real-data run (weak labels)\n\n"
        f"Cases: {len(all_cases)} ({sum(all_labels)} weak-positive). "
        "Labels are heuristic proxies, not confirmed breakage: absence of a revert or fix "
        "commit does not mean an update was safe, and a revert does not always mean breakage. "
        "Treat every number below as a pipeline smoke test, not evidence.\n\n"
        "## Per-rule metrics\n\n"
        "| Rule | Precision | Recall | F1 |\n| --- | --- | --- | --- |\n"
        + "".join(
            f"| {rule} | {m.precision:.2f} | {m.recall:.2f} | {m.f1:.2f} |\n"
            for rule, m in scores.items()
        )
        + f"\nAblation delta F1 (usage minus metadata): {ablation.delta_f1:+.2f}\n"
    )
    (out / "README.md").write_text(readme)
    print(readme)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
