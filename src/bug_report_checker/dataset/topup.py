"""Top up train with public reports that likely lack an expected or actual result (D13).

Run 1 learned each check's prior: expected (18% missing in train) and actual (7%) are
almost always answered "present". laya has no class weights, so the rare class needs
more real examples. Reports are drawn from the same pool as `sample_public`, never from
an eval project, and a dev set is split off to compare runs without touching eval.

Dev mixes enriched and plain reports, so false "missing" answers count as well.
The heuristic finds missing expected results but few missing actual ones, so task-like
reports are also written out to be labelled and kept only where actual is missing.

Usage:
  python -m bug_report_checker.dataset.topup sample <bugs.jsonl.gz> <tokenizer.json>
         <data_dir> <out_dir>
  python -m bug_report_checker.dataset.topup merge <data_dir> <interim_dir>
         <teacher_dir> → data/train_v2.jsonl, data/labels_train_v2.jsonl, data/dev.jsonl
"""

import json
import random
import re
import sys
from pathlib import Path

from bug_report_checker.dataset.assemble import _public_row
from bug_report_checker.dataset.sample_public import POOL_RATE, ROOM, SEED

SIZES = (160, 40, 40, 300)  # train (enriched), dev enriched, dev plain, mine
_EXPECTED_WORDS = re.compile(
    r"\b(?:expect\w*|should|instead|supposed|must|correct(?:ly)?)\b", re.I
)
_TASK_START = re.compile(
    r"^\W*(?:add|allow|support|update|upgrade|improve|implement|remove|make|use"
    r"|create|enable|refactor|document|provide|introduce|need|please)\b",
    re.I,
)


def likely_missing(summary: str, description: str) -> set[str]:
    """A heuristic for sampling, not a label: the teacher decides."""
    parts = set()
    if not _EXPECTED_WORDS.search(f"{summary}\n{description}"):
        parts.add("expected")
    if _TASK_START.search(summary) or summary.rstrip().endswith("?"):
        parts.add("actual")
    return parts


def select(
    cands: list[dict],
    used_ids: set[str],
    eval_projects: set[tuple[str, str]],
    sizes: tuple[int, int, int] = SIZES,
    rng: random.Random | None = None,
) -> tuple[list[dict], list[dict], list[dict]]:
    rng = rng or random.Random(SEED)
    n_train, n_dev_enriched, n_dev_plain, n_mine = sizes
    pool = [
        c
        for c in cands
        if c["tokens"] <= ROOM
        and f"{c['tracker']}:{c['key']}" not in used_ids
        and (c["tracker"], c["project"]) not in eval_projects
    ]
    rng.shuffle(pool)
    enriched = [c for c in pool if likely_missing(c["summary"] or "", c["description"])]
    train = enriched[:n_train]
    dev = enriched[n_train : n_train + n_dev_enriched]
    taken = {id(c) for c in train + dev}
    dev += [c for c in pool if id(c) not in taken][:n_dev_plain]
    taken = {id(c) for c in train + dev}
    mine = [
        c for c in pool if id(c) not in taken and _TASK_START.search(c["summary"] or "")
    ][:n_mine]
    return train, dev, mine


def split_mined(
    rows: list[dict], labels: dict[str, dict], rng: random.Random | None = None
) -> tuple[list[dict], list[dict]]:
    """Mined reports the teacher found without an actual result: 2/3 train, 1/3 dev."""
    kept = [r for r in rows if not labels[r["id"]]["actual"]]
    (rng or random.Random(SEED)).shuffle(kept)
    cut = round(len(kept) * 2 / 3)
    return kept[:cut], kept[cut:]


def _read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines()]


def _write(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def merge(data_dir: Path, interim: Path, teacher: Path) -> None:
    labels = {
        r["id"]: r
        for path in (
            data_dir / "labels_sonnet.jsonl",
            *(
                teacher / f"topup_{n}_sonnet/labels.jsonl"
                for n in ("train", "dev", "mine")
            ),
        )
        for r in _read(path)
    }
    mine_train, mine_dev = split_mined(_read(interim / "topup_mine.jsonl"), labels)
    train = _read(data_dir / "train.jsonl") + _read(interim / "topup_train.jsonl")
    train += mine_train
    dev = _read(interim / "topup_dev.jsonl") + mine_dev
    _write(data_dir / "train_v2.jsonl", train)
    _write(data_dir / "labels_train_v2.jsonl", [labels[r["id"]] for r in train])
    _write(data_dir / "dev.jsonl", [{**r, **labels[r["id"]]} for r in dev])
    print("train_v2", len(train), "| dev", len(dev))


def sample(argv: list[str]) -> None:
    from tokenizers import Tokenizer

    from bug_report_checker.dataset.sample_public import load_candidates

    bugs_path, tokenizer_path = Path(argv[0]), argv[1]
    data_dir, out_dir = Path(argv[2]), Path(argv[3])
    used = [r for name in ("train", "eval") for r in _read(data_dir / f"{name}.jsonl")]
    eval_projects = {
        (r["tracker"], r["project"]) for r in _read(data_dir / "eval.jsonl")
    }
    cands = load_candidates(
        bugs_path, Tokenizer.from_file(tokenizer_path), POOL_RATE, SEED
    )
    train, dev, mine = select(cands, {r["id"] for r in used}, eval_projects)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, part in (
        ("topup_train", train),
        ("topup_dev", dev),
        ("topup_mine", mine),
    ):
        with open(out_dir / f"{name}.jsonl", "w", encoding="utf-8", newline="\n") as f:
            f.writelines(
                json.dumps(_public_row(c), ensure_ascii=False) + "\n" for c in part
            )
        print(name, len(part))


def main(argv: list[str]) -> None:
    if argv[0] == "sample":
        sample(argv[1:])
    elif argv[0] == "merge":
        merge(*map(Path, argv[1:4]))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
