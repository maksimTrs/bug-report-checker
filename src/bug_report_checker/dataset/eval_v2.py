"""Eval v2 (D18): a fresh eval from projects that no other set uses.

Eval v1 was read while planning run 3, so it became dev. Eval v2 is drawn by the
`sample_public` scheme (tracker quotas, length buckets, rare parts weighted) from
projects absent from train, dev and eval v1. A random core is set aside before any
label is seen. Sonnet labels the rest, and only reports it finds without an actual or
expected result join eval, so the two weak checks get enough cases to measure recall.
The added part is not a random draw: precision and accuracy are read on the core only.

Usage:
  python -m bug_report_checker.dataset.eval_v2 sample <bugs.jsonl.gz>
         <tokenizer.json> <pool.jsonl> <used.jsonl> ...
  python -m bug_report_checker.dataset.eval_v2 select <pool.jsonl>
         <sonnet_labels.jsonl> <out.jsonl>
"""

import json
import random
import sys
from collections import Counter
from pathlib import Path

from bug_report_checker.dataset.assemble import _public_row
from bug_report_checker.dataset.sample_public import (
    POOL_RATE,
    ROOM,
    _resize,
    load_candidates,
    pick,
    tracker_quotas,
)

SEED = 20261009  # not eval v1's: a different 5% of the bugs
SIZES = (450, 50)  # fits ROOM, longer — eval v1's 9:1
CORE_SIZES = (90, 10)
EXTRA = 70


def sample(
    cands: list[dict],
    used_projects: set[tuple[str, str]],
    sizes: tuple[int, int] = SIZES,
    core_sizes: tuple[int, int] = CORE_SIZES,
    rng: random.Random | None = None,
) -> list[dict]:
    """The pool for Sonnet, as public rows; `core` marks the random eval core."""
    rng = rng or random.Random(SEED)
    n_fit, n_long = sizes
    free = [c for c in cands if (c["tracker"], c["project"]) not in used_projects]
    fit = [c for c in free if c["tokens"] <= ROOM]
    quotas = tracker_quotas(Counter(c["tracker"] for c in fit), n_fit)
    chosen = []
    for tracker, quota in sorted(quotas.items()):
        chosen += pick([c for c in fit if c["tracker"] == tracker], quota, rng)
    chosen = _resize(chosen, fit, n_fit, rng)
    long_ = rng.sample([c for c in free if c["tokens"] > ROOM], n_long)
    core = {id(c) for c in rng.sample(chosen, core_sizes[0])}
    core |= {id(c) for c in rng.sample(long_, core_sizes[1])}
    return [{**_public_row(c), "core": id(c) in core} for c in chosen + long_]


def select(
    pool: list[dict],
    labels: dict[str, dict],
    n_extra: int = EXTRA,
    rng: random.Random | None = None,
) -> list[dict]:
    """The core plus `n_extra` reports with a gap, half of them missing actual.

    Missing actual is the rarer gap, so it gets its half first; reports that miss only
    expected fill the rest, and missing actual tops up if they run short.
    """
    rng = rng or random.Random(SEED)
    rest = [r for r in pool if not r["core"]]
    rng.shuffle(rest)
    no_actual = [r for r in rest if not labels[r["id"]]["actual"]]
    no_expected = [
        r for r in rest if labels[r["id"]]["actual"] and not labels[r["id"]]["expected"]
    ]
    extra = no_actual[: n_extra // 2]
    extra += no_expected[: n_extra - len(extra)]
    extra += no_actual[n_extra // 2 :][: n_extra - len(extra)]
    return [r for r in pool if r["core"]] + extra


def check_unused(eval_v2: list[dict], other: list[dict]) -> None:
    shared = {(r["tracker"], r["project"]) for r in eval_v2} & {
        (r["tracker"], r["project"]) for r in other
    }
    if shared:
        raise ValueError(f"eval v2 projects used elsewhere: {sorted(shared)}")


def _read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines()]


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def main(argv: list[str]) -> None:
    if argv[0] == "sample":
        from tokenizers import Tokenizer

        used = [r for path in argv[4:] for r in _read(Path(path))]
        cands = load_candidates(
            Path(argv[1]), Tokenizer.from_file(argv[2]), POOL_RATE, SEED
        )
        pool = sample(cands, {(r["tracker"], r["project"]) for r in used})
        check_unused(pool, used)
        _write(Path(argv[3]), pool)
        print("pool", len(pool), "| core", sum(r["core"] for r in pool))
        print("  trackers:", dict(Counter(r["tracker"] for r in pool).most_common()))
    elif argv[0] == "select":
        labels = {r["id"]: r for r in _read(Path(argv[2]))}
        chosen = select(_read(Path(argv[1])), labels)
        _write(Path(argv[3]), chosen)
        gaps = {
            c: sum(not labels[r["id"]][c] for r in chosen)
            for c in ("actual", "expected")
        }
        print("eval v2", len(chosen), "| Sonnet finds missing:", gaps)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
