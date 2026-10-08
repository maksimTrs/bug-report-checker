"""Labelled reports → Laya typed-decisions rows: `{id, state, questions, gold}`.

The state is the preprocessed `{summary, description}` the model sees at inference; each
check becomes a `noul` question. Targets are hard (P = 1.0 on the teacher's answer) or,
with `smoothing` ε, (1 − ε/2, ε/2): run 1 on hard targets came out overconfident (D12).
laya's own `label_smoothing` applies only to `expected` rows, not to `gold`.

Usage: python -m bug_report_checker.dataset.laya_format <reports.jsonl> <labels.jsonl>
       <out.jsonl> [smoothing]   (labels may be the reports file itself, as in
       eval/eval.jsonl)
"""

import json
import sys
from pathlib import Path

from bug_report_checker.labeling import CHECKS
from bug_report_checker.questions import laya_questions


def _target(label: bool, smoothing: float) -> dict[str, float]:
    high, low = 1.0 - smoothing / 2, smoothing / 2
    return {"false": low if label else high, "true": high if label else low}


def to_laya_rows(
    reports: list[dict], labels: list[dict], smoothing: float = 0.0
) -> list[dict]:
    by_id = {r["id"]: r for r in labels}
    if missing := [r["id"] for r in reports if r["id"] not in by_id]:
        raise ValueError(f"no labels for {missing}")
    questions = laya_questions()
    return [
        {
            "id": r["id"],
            "state": {"summary": r["summary"], "description": r["description"]},
            "questions": questions,
            "gold": {
                check: {
                    "probabilities": _target(by_id[r["id"]][check], smoothing),
                    "label": by_id[r["id"]][check],
                }
                for check in CHECKS
            },
        }
        for r in reports
    ]


def _read(path: str) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text("utf-8").splitlines()]


def main(argv: list[str]) -> None:
    smoothing = float(argv[3]) if len(argv) > 3 else 0.0
    rows = to_laya_rows(_read(argv[0]), _read(argv[1]), smoothing)
    with open(argv[2], "w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    print(argv[2], len(rows), "rows,", len(rows) * len(CHECKS), "decisions")


if __name__ == "__main__":
    main(sys.argv[1:])
