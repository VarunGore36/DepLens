from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path

from deplens.evaluation import ablate, brier_score, results_table, roc_auc, score_rules
from deplens.prediction import UpdateCase, run_baselines

DATASET = Path(__file__).parent.parent / "datasets" / "v0" / "cases.jsonl"


def load_cases(path: Path = DATASET) -> tuple[list[UpdateCase], list[bool]]:
    cases, labels = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        cases.append(
            UpdateCase(
                package=row["package"],
                old_version=row.get("old_version"),
                new_version=row.get("new_version"),
                direct=row["direct"],
                depth=row["depth"],
                affected_imports=row["affected_imports"],
                affected_apis=row["affected_apis"],
            )
        )
        labels.append(bool(row["label"]))
    return cases, labels


def main() -> int:
    parser = argparse.ArgumentParser(description="Reproduce DepLens v0 results")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    cases, labels = load_cases()
    scores = score_rules(cases, labels)
    by_rule: dict[str, list] = {rule: [] for rule in scores}
    for case in cases:
        for pred in run_baselines(case):
            by_rule[pred.rule].append(pred)
    rules = sorted(scores)
    probs = {rule: [p.score for p in by_rule[rule]] for rule in rules}
    table = results_table(scores, probs, labels)
    ablation = ablate(cases, labels)
    print(f"n={len(cases)}, positives={sum(labels)}")
    print(table)
    print(f"\nablation delta F1 (usage minus metadata): {ablation.delta_f1:+.2f}")
    print(f"mean ROC-AUC: {sum(roc_auc(labels, probs[r]) for r in rules) / len(rules):.2f}")
    print(f"mean Brier: {sum(brier_score(labels, probs[r]) for r in rules) / len(rules):.2f}")
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        metrics = {
            "n_cases": len(cases),
            "n_positive": sum(labels),
            "rules": {rule: dataclasses.asdict(m) for rule, m in scores.items()},
            "roc_auc": {rule: roc_auc(labels, probs[rule]) for rule in rules},
            "brier": {rule: brier_score(labels, probs[rule]) for rule in rules},
            "ablation_delta_f1": ablation.delta_f1,
        }
        (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
