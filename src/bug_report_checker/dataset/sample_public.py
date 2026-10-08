"""Stratified sample of public bugs for labeling: 220 train, 100 eval.

- Projects are split first: no project is in both train and eval, so eval measures
  generalization, not memorized project style. `check_disjoint` enforces it.
- Tracker quotas grow with the square root of the tracker size, so Apache and Mojang
  (62% of bugs) do not crowd out the small trackers.
- Within a tracker, three length buckets (tokens of the preprocessed state); reports
  with rare parts (explicit steps or expected result, version, headed template) are
  three times as likely to be picked.
- Train holds only states that fit `ROOM`: training keeps the start of a longer state,
  while the teacher sees all of it. A few long reports go to eval for `predict_long`.

Usage: python -m bug_report_checker.dataset.sample_public \
    <bugs.jsonl.gz> <tokenizer.json> <out_dir>
"""

import gzip
import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path

from bug_report_checker.dataset.token_stats import state_tokens
from bug_report_checker.preprocess import preprocess

SEED = 20261008
POOL_RATE = 0.05
ROOM = 767  # worst-case state room of laya-typed-decisions (D6)
SIZES = (220, 90, 10)  # train, eval that fits, eval longer than ROOM
EVAL_SHARE = 0.3  # share of a tracker's candidates whose projects go to eval
BUCKETS = ((0, 60), (61, 250), (251, ROOM))
BUCKET_SHARE = (0.3, 0.4, 0.3)
RARE_WEIGHT = 3

_STEPS_HEADER = re.compile(
    r"^\W*(?:steps|how to reproduce|to reproduce|reproduction)\b", re.I | re.M
)
_NUMBERED = re.compile(r"^\s*\d+[.)]\s+\S", re.M)
_EXPECTED = re.compile(r"\bexpected\b", re.I)
_VERSION = re.compile(r"\b(?:version|build)\s*:?\s*#?v?\d|\b\d+\.\d+\.\d+", re.I)
_SECTION_HEADER = re.compile(
    r"^\s*(?:#{1,6}\s*|\*\*)(steps|expected|actual|observed)", re.I | re.M
)


def flags(description: str) -> dict[str, bool]:
    """Rare parts of a report (T1.10), a heuristic for sampling, not a label."""
    return {
        "steps": bool(_STEPS_HEADER.search(description))
        or len(_NUMBERED.findall(description)) >= 2,
        "expected": bool(_EXPECTED.search(description)),
        "version": bool(_VERSION.search(description)),
        "template": len({m.lower() for m in _SECTION_HEADER.findall(description)}) >= 2,
    }


def tracker_quotas(
    counts: dict[str, int], total: int, minimum: int = 2
) -> dict[str, int]:
    """Seats per tracker, proportional to sqrt(size), summing exactly to `total`."""
    weights = {t: math.sqrt(n) for t, n in counts.items()}
    raw = {t: total * w / sum(weights.values()) for t, w in weights.items()}
    quotas = {t: max(minimum, math.floor(r)) for t, r in raw.items()}
    while sum(quotas.values()) < total:
        quotas[max(raw, key=lambda t: raw[t] - quotas[t])] += 1
    while sum(quotas.values()) > total:
        over = [t for t in quotas if quotas[t] > minimum]
        quotas[max(over, key=lambda t: quotas[t] - raw[t])] -= 1
    return quotas


def split_projects(
    cands: list[dict], share: float, rng: random.Random
) -> set[tuple[str, str]]:
    """Eval projects: random projects of each tracker until `share` of its bugs."""
    sizes = Counter((c["tracker"], c["project"]) for c in cands)
    eval_projects = set()
    for tracker in sorted({t for t, _ in sizes}):
        projects = sorted(p for t, p in sizes if t == tracker)
        rng.shuffle(projects)
        target = share * sum(sizes[tracker, p] for p in projects)
        taken = 0
        for project in projects[:-1]:  # the last one always stays in train
            if taken >= target:
                break
            eval_projects.add((tracker, project))
            taken += sizes[tracker, project]
    return eval_projects


def check_disjoint(train: list[dict], eval_: list[dict]) -> None:
    shared = {(c["tracker"], c["project"]) for c in train} & {
        (c["tracker"], c["project"]) for c in eval_
    }
    if shared:
        raise ValueError(f"projects in both train and eval: {sorted(shared)}")


def _weighted(pool: list[dict], n: int, rng: random.Random) -> list[dict]:
    """`n` items without replacement, rare-part reports `RARE_WEIGHT` times likelier."""

    def key(c: dict) -> float:
        weight = RARE_WEIGHT if any(c["flags"].values()) else 1
        return rng.random() ** (1 / weight)

    return sorted(pool, key=key, reverse=True)[:n]


def pick(pool: list[dict], n: int, rng: random.Random) -> list[dict]:
    """`n` reports spread over the length buckets; short buckets are topped up."""
    targets = [round(n * share) for share in BUCKET_SHARE]
    targets[1] += n - sum(targets)
    chosen = []
    for (low, high), k in zip(BUCKETS, targets, strict=True):
        chosen += _weighted([c for c in pool if low <= c["tokens"] <= high], k, rng)
    taken = {id(c) for c in chosen}
    rest = [c for c in pool if id(c) not in taken]
    return chosen + _weighted(rest, n - len(chosen), rng)


def _resize(
    chosen: list[dict], pool: list[dict], n: int, rng: random.Random
) -> list[dict]:
    """Rounding leaves a split a few seats off: trim the largest tracker or top up."""
    chosen = list(chosen)
    while len(chosen) > n:
        largest = Counter(c["tracker"] for c in chosen).most_common(1)[0][0]
        chosen.remove(next(c for c in reversed(chosen) if c["tracker"] == largest))
    taken = {id(c) for c in chosen}
    return chosen + pick([c for c in pool if id(c) not in taken], n - len(chosen), rng)


def sample(
    cands: list[dict], seed: int = SEED, sizes: tuple[int, int, int] = SIZES
) -> tuple[list[dict], list[dict]]:
    n_train, n_eval, n_long = sizes
    rng = random.Random(seed)
    eval_projects = split_projects(cands, EVAL_SHARE, rng)

    def in_eval(c: dict) -> bool:
        return (c["tracker"], c["project"]) in eval_projects

    fit = [c for c in cands if c["tokens"] <= ROOM]
    quotas = tracker_quotas(Counter(c["tracker"] for c in fit), n_train + n_eval)
    train, eval_ = [], []
    for tracker, quota in sorted(quotas.items()):
        quota_eval = round(quota * n_eval / (n_train + n_eval))
        pool = [c for c in fit if c["tracker"] == tracker]
        train += pick([c for c in pool if not in_eval(c)], quota - quota_eval, rng)
        eval_ += pick([c for c in pool if in_eval(c)], quota_eval, rng)
    train = _resize(train, [c for c in fit if not in_eval(c)], n_train, rng)
    eval_ = _resize(eval_, [c for c in fit if in_eval(c)], n_eval, rng)
    long_ = [c for c in cands if c["tokens"] > ROOM and in_eval(c)]
    eval_ += rng.sample(long_, n_long)
    check_disjoint(train, eval_)
    return train, eval_


def load_candidates(bugs_path: Path, tokenizer, rate: float, seed: int) -> list[dict]:
    """A random `rate` of bugs with a description, with state tokens and rare parts."""
    rng = random.Random(seed)
    records = []
    with gzip.open(bugs_path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if rng.random() >= rate:
                continue
            record = json.loads(line)
            if (record["description"] or "").strip():
                records.append(record)
    for record, tokens in zip(records, state_tokens(tokenizer, records), strict=True):
        state = preprocess(record["summary"] or "", record["description"], jira=True)
        record["tokens"] = tokens
        record["flags"] = flags(state["description"])
    return records


def _report(name: str, part: list[dict]) -> None:
    trackers = Counter(c["tracker"] for c in part)
    buckets = Counter(
        next((f"{lo}-{hi}" for lo, hi in BUCKETS if lo <= c["tokens"] <= hi), "long")
        for c in part
    )
    rare = {f: sum(c["flags"][f] for c in part) for f in part[0]["flags"]}
    projects = len({(c["tracker"], c["project"]) for c in part})
    print(f"{name}: {len(part)} bugs, {projects} projects")
    print("  trackers:", dict(trackers.most_common()))
    print("  tokens:", dict(sorted(buckets.items())))
    print("  rare parts:", rare)


def main(argv: list[str]) -> None:
    from tokenizers import Tokenizer

    bugs_path, tokenizer_path, out_dir = Path(argv[0]), argv[1], Path(argv[2])
    cands = load_candidates(
        bugs_path, Tokenizer.from_file(tokenizer_path), POOL_RATE, SEED
    )
    train, eval_ = sample(cands)
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = ("key", "tracker", "project", "tokens", "flags", "summary", "description")
    for name, part in (("public_train", train), ("public_eval", eval_)):
        with open(out_dir / f"{name}.jsonl", "w", encoding="utf-8") as out:
            for c in part:
                out.write(json.dumps({f: c[f] for f in fields}, ensure_ascii=False))
                out.write("\n")
        _report(name, part)


if __name__ == "__main__":
    main(sys.argv[1:])
