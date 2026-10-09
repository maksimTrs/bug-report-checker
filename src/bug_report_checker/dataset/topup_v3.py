"""Run 3 data (D20): ordinary reports with a likely gap, and Opus labels throughout.

Run 2 errors on dev v3 (dev + eval v1) on actual / expected are not task-like reports,
which run 2's top-up already covers, but one-liners, descriptions that only restate the
summary, and steps with no result at all. Such reports are sampled from projects outside
both evals, labelled by Opus and kept whole, gap or not: keeping the complete ones stops
the model from learning "short means incomplete".

Train and dev are relabelled by Opus too: Sonnet calls the expected result missing where
the rubric counts a crash or a plain negation as stated (D19), so Sonnet-labelled train
and Opus-labelled eval disagreed on what "missing" means.

Usage:
  python -m bug_report_checker.dataset.topup_v3 sample <bugs.jsonl.gz> <tokenizer.json>
         <data_dir> <out.jsonl>
  python -m bug_report_checker.dataset.topup_v3 merge <data_dir> <mined.jsonl>
         <teacher_dir>
         → data/train_v3.jsonl, data/labels_train_v3.jsonl, data/dev_v3.jsonl
"""

import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

from bug_report_checker.dataset.assemble import _public_row
from bug_report_checker.dataset.sample_public import POOL_RATE, ROOM, tracker_quotas
from bug_report_checker.dataset.topup import _TASK_START

SEED = 20261010  # neither eval's nor run 2's 5% of the bugs
N_MINE = 450
SHORT = 60  # tokens of the state: the shortest length bucket of `sample_public`
_NUMBERED = re.compile(r"^\s*\d+[.)]\s+\S", re.M)
_RESULT_WORDS = re.compile(
    r"\b(?:expect\w*|should|instead|actual\w*|error\w*|exception|fail\w*|crash\w*"
    r"|wrong|broken|result\w*|returns?|shows?|throws?|but)\b",
    re.I,
)


def _words(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.lower()))


def ordinary_gap(summary: str, description: str, tokens: int) -> bool:
    """A heuristic for sampling, not a label: the teacher decides."""
    if _TASK_START.search(summary):
        return False
    short = tokens <= SHORT
    restates = _words(description).startswith(_words(summary))
    steps_only = len(_NUMBERED.findall(description)) >= 2 and not _RESULT_WORDS.search(
        description
    )
    return short or restates or steps_only


def select(
    cands: list[dict],
    used_ids: set[str],
    excluded_projects: set[tuple[str, str]],
    n: int = N_MINE,
    rng: random.Random | None = None,
) -> list[dict]:
    rng = rng or random.Random(SEED)
    pool = [
        c
        for c in cands
        if c["tokens"] <= ROOM
        and f"{c['tracker']}:{c['key']}" not in used_ids
        and (c["tracker"], c["project"]) not in excluded_projects
        and ordinary_gap(c["summary"] or "", c["description"], c["tokens"])
    ]
    # Short reports are mostly Mojang's; sqrt quotas keep one tracker from crowding out.
    quotas = tracker_quotas(Counter(c["tracker"] for c in pool), min(n, len(pool)), 0)
    rng.shuffle(pool)
    return [
        c
        for tracker, quota in sorted(quotas.items())
        for c in [c for c in pool if c["tracker"] == tracker][:quota]
    ]


def split(
    rows: list[dict], rng: random.Random | None = None
) -> tuple[list[dict], list[dict]]:
    """2/3 train, 1/3 dev."""
    rows = list(rows)
    (rng or random.Random(SEED)).shuffle(rows)
    cut = round(len(rows) * 2 / 3)
    return rows[:cut], rows[cut:]


def _read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines()]


def _write(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def merge(data_dir: Path, mined_path: Path, teacher: Path) -> None:
    from bug_report_checker.labeling import CHECKS

    labels = {
        r["id"]: {"id": r["id"], **{c: r[c] for c in CHECKS}}
        for name in ("train_v2_opus", "dev_opus", "topup_v3_opus")
        for r in _read(teacher / name / "labels.jsonl")
    }
    mined_train, mined_dev = split(_read(mined_path))
    train = _read(data_dir / "train_v2.jsonl") + mined_train
    dev = [{**r, **labels[r["id"]]} for r in _read(data_dir / "dev.jsonl") + mined_dev]
    dev += _read(data_dir.parent / "eval" / "eval.jsonl")  # final labels already
    _write(data_dir / "train_v3.jsonl", train)
    _write(data_dir / "labels_train_v3.jsonl", [labels[r["id"]] for r in train])
    _write(data_dir / "dev_v3.jsonl", dev)
    print("train_v3", len(train), "| dev_v3", len(dev))


def sample(argv: list[str]) -> None:
    from tokenizers import Tokenizer

    from bug_report_checker.dataset.sample_public import load_candidates

    bugs_path, tokenizer_path = Path(argv[0]), argv[1]
    data_dir, out = Path(argv[2]), Path(argv[3])
    root = data_dir.parent
    evals = _read(root / "eval" / "eval.jsonl") + _read(root / "eval" / "eval_v2.jsonl")
    used = [
        *_read(data_dir / "train_v2.jsonl"),
        *_read(data_dir / "dev.jsonl"),
        *_read(data_dir / "interim" / "topup_mine.jsonl"),
        *evals,
    ]
    cands = load_candidates(
        bugs_path, Tokenizer.from_file(tokenizer_path), POOL_RATE, SEED
    )
    mined = select(
        cands,
        {r["id"] for r in used},
        {(r["tracker"], r["project"]) for r in evals},
    )
    _write(out, [_public_row(c) for c in mined])
    print("mined", len(mined))


def main(argv: list[str]) -> None:
    if argv[0] == "sample":
        sample(argv[1:])
    elif argv[0] == "merge":
        merge(*map(Path, argv[1:4]))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
