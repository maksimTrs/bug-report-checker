"""Per-check agreement of a label set with a reference set.

Overall agreement hides skewed checks (actual is "yes" in ~90% of reports, so
always answering "yes" scores high), hence the minority class is reported too.

Usage: python -m bug_report_checker.labeling.agreement <reference.jsonl> <labels.jsonl>
       [min_share]   exit code 1 if any check agrees on less than min_share (0.85)
"""

import json
import sys
from pathlib import Path

from bug_report_checker.labeling import CHECKS


def agreement(reference: list[dict], labels: list[dict]) -> dict[str, dict]:
    ref = {r["id"]: r for r in reference}
    got = {r["id"]: r for r in labels}
    if ref.keys() != got.keys():
        raise ValueError(
            f"id sets differ — missing: {sorted(ref.keys() - got.keys())},"
            f" extra: {sorted(got.keys() - ref.keys())}"
        )
    stats = {}
    for check in CHECKS:
        yes = sum(r[check] for r in ref.values())
        minority = yes < len(ref) - yes  # a tie counts "no" as the minority
        stats[check] = {
            "n": len(ref),
            "agree": sum(ref[i][check] == got[i][check] for i in ref),
            "minority": minority,
            "minority_n": sum(r[check] == minority for r in ref.values()),
            "minority_agree": sum(
                ref[i][check] == got[i][check] == minority for i in ref
            ),
        }
    return stats


def report(stats: dict[str, dict], min_share: float) -> tuple[str, bool]:
    """Markdown table and whether every check reaches min_share."""
    lines = [
        "| Check | Agreement | Minority class | Minority agreement |",
        "|---|---|---|---|",
    ]
    ok = True
    for check, s in stats.items():
        passed = s["agree"] >= min_share * s["n"]
        ok &= passed
        lines.append(
            f"| {check} | {s['agree']}/{s['n']}{'' if passed else ' FAIL'} |"
            f" {'yes' if s['minority'] else 'no'} ({s['minority_n']}) |"
            f" {s['minority_agree']}/{s['minority_n']} |"
        )
    return "\n".join(lines), ok


def _read(path: str) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text("utf-8").splitlines()]


def main(argv: list[str]) -> int:
    min_share = float(argv[2]) if len(argv) > 2 else 0.85
    table, ok = report(agreement(_read(argv[0]), _read(argv[1])), min_share)
    print(table)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
