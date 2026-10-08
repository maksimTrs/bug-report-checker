"""Token length of preprocessed bug reports, counted the way Laya counts the state.

Laya serializes the state to JSON and tokenizes it without special tokens; the state
gets `max_len - question head - 1` tokens, the rest is cut off. Room 767 is the worst
case for `laya-typed-decisions` (max_len 1024, head_max_len 256); 895: 128-token head.

Usage: python -m bug_report_checker.dataset.token_stats \
    <bugs.jsonl.gz> <tokenizer.json> [sample_rate]
"""

import gzip
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from statistics import quantiles

from laya.common import serialize_state

from bug_report_checker.preprocess import preprocess

ROOMS = (767, 895)


def state_tokens(tokenizer, records: list[dict]) -> list[int]:
    """Tokens of each record's preprocessed state (Jira wiki source)."""
    texts = [
        serialize_state(preprocess(r["summary"] or "", r["description"], jira=True))
        for r in records
    ]
    encodings = tokenizer.encode_batch(texts, add_special_tokens=False)
    return [len(e.ids) for e in encodings]


def summarize(lengths: list[int], rooms: tuple[int, ...] = ROOMS) -> dict:
    """Median, p90, p99 and the share of states longer than each room."""
    q = quantiles(lengths, n=100, method="inclusive")
    return {
        "n": len(lengths),
        "median": round(q[49]),
        "p90": round(q[89]),
        "p99": round(q[98]),
        "over": {room: sum(n > room for n in lengths) / len(lengths) for room in rooms},
    }


def main(argv: list[str]) -> None:
    from tokenizers import Tokenizer

    bugs_path, tokenizer_path = Path(argv[0]), argv[1]
    rate = float(argv[2]) if len(argv) > 2 else 0.05
    tokenizer = Tokenizer.from_file(tokenizer_path)
    rng = random.Random(0)
    by_tracker: dict[str, list[dict]] = defaultdict(list)
    with gzip.open(bugs_path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if rng.random() >= rate:
                continue
            record = json.loads(line)
            if (record["description"] or "").strip():
                by_tracker[record["tracker"]].append(record)

    over = " | ".join(f"> {room}" for room in ROOMS)
    print(f"| Tracker | Sample | Median | p90 | p99 | {over} |")
    print("|---|---:|---:|---:|---:|" + "---:|" * len(ROOMS))
    lengths = {t: state_tokens(tokenizer, rs) for t, rs in sorted(by_tracker.items())}
    rows = [*lengths.items(), ("**Total**", [n for ls in lengths.values() for n in ls])]
    for tracker, ls in rows:
        s = summarize(ls)
        shares = " | ".join(f"{share:.1%}" for share in s["over"].values())
        print(
            f"| {tracker} | {s['n']:,} | {s['median']} | {s['p90']} | {s['p99']}"
            f" | {shares} |"
        )


if __name__ == "__main__":
    main(sys.argv[1:])
