"""Per-check evaluation of a Laya checkpoint on a labelled set.

"Missing" is the class that matters: the bot exists to say what a report lacks, and
labels are skewed towards "present", so overall accuracy flatters a model that always
says yes. Each check reports recall and precision of "missing" with a 95% Wilson
interval.

Usage:
  python -m bug_report_checker.evaluate predict <checkpoint> <eval.jsonl> <preds.jsonl>
  python -m bug_report_checker.evaluate report <eval.jsonl> <name>=<preds.jsonl> ...
  python -m bug_report_checker.evaluate bot <eval.jsonl> <preds.jsonl> <threshold>
"""

import json
import math
import sys
from pathlib import Path

from laya.evals import ece

from bug_report_checker.labeling import CHECKS
from bug_report_checker.questions import laya_questions

Z95 = 1.96


def wilson(hits: int, n: int) -> tuple[float | None, float | None]:
    """95% Wilson interval: honest at small n and near 0 or 1, unlike p ± 1.96·se."""
    if n == 0:
        return None, None
    p = hits / n
    centre = (p + Z95**2 / (2 * n)) / (1 + Z95**2 / n)
    half = Z95 * math.sqrt(p * (1 - p) / n + Z95**2 / (4 * n * n)) / (1 + Z95**2 / n)
    return max(0.0, centre - half), min(1.0, centre + half)  # float noise at 0 and 1


def check_metrics(gold: list[bool], p_true: list[float]) -> dict:
    """One check at the 0.5 cut; "missing" (gold False) is the positive class."""
    pred = [p >= 0.5 for p in p_true]
    correct = [g == y for g, y in zip(gold, pred, strict=True)]
    conf = [max(p, 1 - p) for p in p_true]
    no_n = sum(not g for g in gold)
    said_no = sum(not y for y in pred)
    found = sum(not g and not y for g, y in zip(gold, pred, strict=True))
    return {
        "n": len(gold),
        "accuracy": sum(correct) / len(gold),
        "accuracy_ci": wilson(sum(correct), len(gold)),
        "no_n": no_n,
        "no_found": found,
        "recall_no": found / no_n if no_n else None,
        "recall_no_ci": wilson(found, no_n),
        "precision_no": found / said_no if said_no else None,
        "mean_confidence": sum(conf) / len(conf),
        "ece": ece(conf, correct),
    }


def bot_metrics(gold: list[bool], p_true: list[float], threshold: float) -> dict:
    """The bot's view: below `threshold` confidence it says "not sure" instead."""
    decided = [max(p, 1 - p) >= threshold for p in p_true]
    said = [None if not d else p >= 0.5 for d, p in zip(decided, p_true, strict=True)]
    right = [y == g for g, y in zip(gold, said, strict=True) if y is not None]
    pairs = list(zip(gold, said, strict=True))
    return {
        "n": len(gold),
        "coverage": len(right) / len(gold),
        "accuracy_decided": sum(right) / len(right) if right else None,
        "no_n": sum(not g for g in gold),
        "no_said_no": sum(not g and y is False for g, y in pairs),
        "no_unsure": sum(not g and y is None for g, y in pairs),
        "no_said_yes": sum(not g and y is True for g, y in pairs),
        "yes_said_no": sum(g and y is False for g, y in pairs),
    }


def predict(checkpoint: str, rows: list[dict]) -> list[dict]:
    """P(true) per check for every report; long reports are scanned in windows."""
    import laya

    agent = laya.load(checkpoint, device="cpu")
    questions = laya_questions()
    out = []
    for n, r in enumerate(rows, 1):
        state = {"summary": r["summary"], "description": r["description"]}
        answers = agent.predict_long(state, questions)["answers"]
        out.append({"id": r["id"], **{c: answers[c]["noul"] for c in CHECKS}})
        if n % 10 == 0:
            print(f"{n}/{len(rows)}", flush=True)
    return out


def _pct(v: float | None) -> str:
    return "—" if v is None else f"{100 * v:.0f}%"


def report(rows: list[dict], preds: dict[str, list[dict]]) -> str:
    """Markdown: one table per check, a row per model plus the always-yes baseline."""
    lines = []
    for check in CHECKS:
        gold = [r[check] for r in rows]
        lines += [
            f"### {check}",
            "",
            "| Model | Accuracy (95% CI) | Recall missing (95% CI) |"
            " Precision missing | Confidence | ECE |",
            "|---|---|---|---|---|---|",
        ]
        models = {"always yes": [1.0] * len(rows)}
        for name, p in preds.items():
            by_id = {x["id"]: x for x in p}
            models[name] = [by_id[r["id"]][check] for r in rows]
        for name, p_true in models.items():
            m = check_metrics(gold, p_true)
            lo, hi = m["accuracy_ci"]
            rlo, rhi = m["recall_no_ci"]
            ece_cell = "—" if m["ece"] is None else f"{m['ece']:.3f}"
            lines.append(
                f"| {name} | {_pct(m['accuracy'])} ({_pct(lo)}–{_pct(hi)}) |"
                f" {m['no_found']}/{m['no_n']} = {_pct(m['recall_no'])}"
                f" ({_pct(rlo)}–{_pct(rhi)}) | {_pct(m['precision_no'])} |"
                f" {m['mean_confidence']:.2f} | {ece_cell} |"
            )
        lines.append("")
    return "\n".join(lines)


def bot_report(rows: list[dict], preds: list[dict], threshold: float) -> str:
    """Markdown: what the bot would say per check at the calibrated threshold."""
    by_id = {x["id"]: x for x in preds}
    lines = [
        f'Threshold {threshold}: below it the bot says "not sure".',
        "",
        "| Check | Coverage | Accuracy decided | Missing → missing / not sure /"
        " present | Present → missing |",
        "|---|---|---|---|---|",
    ]
    for check in CHECKS:
        gold = [r[check] for r in rows]
        m = bot_metrics(gold, [by_id[r["id"]][check] for r in rows], threshold)
        lines.append(
            f"| {check} | {_pct(m['coverage'])} | {_pct(m['accuracy_decided'])} |"
            f" {m['no_said_no']} / {m['no_unsure']} / {m['no_said_yes']}"
            f" of {m['no_n']} | {m['yes_said_no']} of {m['n'] - m['no_n']} |"
        )
    return "\n".join(lines)


def _read(path: str) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text("utf-8").splitlines()]


def main(argv: list[str]) -> None:
    if argv[0] == "predict":
        preds = predict(argv[1], _read(argv[2]))
        with open(argv[3], "w", encoding="utf-8", newline="\n") as f:
            f.writelines(json.dumps(p) + "\n" for p in preds)
    elif argv[0] == "report":
        named = dict(arg.split("=", 1) for arg in argv[2:])
        print(report(_read(argv[1]), {k: _read(v) for k, v in named.items()}))
    elif argv[0] == "bot":
        print(bot_report(_read(argv[1]), _read(argv[2]), float(argv[3])))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
