"""Assemble the labeling sets: train (public + synthetic), eval (public), style-eval.

Text is stored preprocessed — the teacher labels exactly what the model will see.
Public reports are Jira wiki, synthetic ones markdown.

Usage: python -m bug_report_checker.dataset.assemble <interim_dir> <out_dir>
"""

import json
import random
import sys
from collections import Counter
from pathlib import Path

from bug_report_checker.dataset.sample_public import SEED, check_disjoint
from bug_report_checker.preprocess import preprocess

FIELDS = ("id", "source", "tracker", "project", "summary", "description")
SIZES = {"train": (220, 80), "eval": (100, 0), "style_eval": (0, 30)}  # public, syn
SYNTHETIC_TRACKER = "Parcelwise"


def _public_row(r: dict) -> dict:
    state = preprocess(r["summary"] or "", r["description"], jira=True)
    return {
        "id": f"{r['tracker']}:{r['key']}",
        "source": "public",
        "tracker": r["tracker"],
        "project": r["project"],
        **state,
    }


def _synthetic_row(r: dict) -> dict:
    state = preprocess(r["summary"], r["description"])
    return {
        "id": r["id"],
        "source": "synthetic",
        "tracker": SYNTHETIC_TRACKER,
        "project": r["area"],
        **state,
    }


def assemble(
    public_train: list[dict],
    public_eval: list[dict],
    synthetic: list[dict],
    seed: int = SEED,
) -> dict[str, list[dict]]:
    synthetic_rows = sorted(map(_synthetic_row, synthetic), key=lambda r: r["id"])
    sets = {
        "train": [*map(_public_row, public_train)]
        + [r for r in synthetic_rows if r["id"].startswith("syn-train-")],
        "eval": sorted(map(_public_row, public_eval), key=lambda r: r["id"]),
        "style_eval": [r for r in synthetic_rows if r["id"].startswith("syn-style-")],
    }
    random.Random(seed).shuffle(sets["train"])  # mix public and synthetic
    return sets


def validate(sets: dict[str, list[dict]], sizes: dict = SIZES) -> None:
    """Raise on wrong counts, schema, empty text, duplicate ids, shared projects."""
    errors = []
    for name, (public, synthetic) in sizes.items():
        got = Counter(r.get("source") for r in sets[name])
        if (got["public"], got["synthetic"]) != (public, synthetic):
            errors.append(
                f"{name}: expected {public} public + {synthetic} synthetic,"
                f" got {got['public']} + {got['synthetic']}"
            )
    rows = [r for rows in sets.values() for r in rows]
    for r in rows:
        if set(r) != set(FIELDS):
            errors.append(f"unexpected fields in {r.get('id')}: {sorted(r)}")
        for field in FIELDS:
            if not isinstance(r.get(field), str) or not r[field].strip():
                errors.append(f"empty {field} in {r.get('id')}")
    if duplicates := [
        i for i, n in Counter(r.get("id") for r in rows).items() if n > 1
    ]:
        errors.append(f"duplicate ids: {sorted(duplicates)}")
    try:
        check_disjoint(
            [r for r in sets["train"] if r.get("source") == "public"], sets["eval"]
        )
    except ValueError as e:
        errors.append(str(e))
    if errors:
        raise ValueError("; ".join(errors))


def _read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines()]


def main(argv: list[str]) -> None:
    interim, out_dir = Path(argv[0]), Path(argv[1])
    specs = json.loads((interim / "synthetic_specs.json").read_text("utf-8"))
    area = {s["id"]: s["area"] for s in specs["train"] + specs["style"]}
    synthetic = [
        {**r, "area": area[r["id"]]} for r in _read(interim / "synthetic.jsonl")
    ]
    sets = assemble(
        _read(interim / "public_train.jsonl"),
        _read(interim / "public_eval.jsonl"),
        synthetic,
    )
    validate(sets)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in sets.items():
        with open(out_dir / f"{name}.jsonl", "w", encoding="utf-8") as out:
            out.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        print(name, len(rows), dict(Counter(r["source"] for r in rows)))


if __name__ == "__main__":
    main(sys.argv[1:])
