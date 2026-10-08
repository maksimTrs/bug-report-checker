"""Coverage plan for synthetic bug reports and a check of what the generator returned.

Each spec names 1-3 variations (gaps a real report has: no build, steps unknown,
result only as a screenshot, ...). Train specs cover every variation at least
`TRAIN_MIN` times; style-eval specs add a few very long, spec-like reports.

Usage:
    python -m bug_report_checker.dataset.synthetic_plan specs <specs.json>
    python -m bug_report_checker.dataset.synthetic_plan check <specs.json> <out.jsonl>
"""

import json
import random
import re
import sys
from collections import Counter
from itertools import combinations, product
from pathlib import Path

SEED = 20261008
TRAIN_MIN = 8
BUILD = ("build_empty", "build_os", "build_moving")
FIELD = ("steps_unknown", "image_only", "expected_question", "expected_struck")
FREE = ("free_one_line", "free_trace")
SUMMARY = ("tag_summary", "task_summary")
AREAS = ("Booking", "Tracking", "Billing", "Depots", "Couriers", "Admin", "API")
BODY = ("full", *BUILD, *FIELD, *FREE, "links_tables", "spec_long")

# A full report has no gaps; free form and spec-like reports have no template fields.
_CLASHES = (
    (("full",), (*BUILD, *FIELD, *FREE, "spec_long")),
    (FREE, (*BUILD, *FIELD, "links_tables", "spec_long")),
    (("spec_long",), (*BUILD, *FIELD, "links_tables")),
)
INCOMPATIBLE = [
    frozenset(pair)
    for group in (BUILD, FIELD, FREE, SUMMARY)
    for pair in combinations(group, 2)
] + [frozenset(pair) for left, right in _CLASHES for pair in product(left, right)]

_URL_HOST = re.compile(r"https?://([^/\s)\]>\"'`]+)")
_CODES = "|".join(c for c in (*BODY, *SUMMARY) if "_" in c)  # `full` is a plain word
_CODE_IN_TEXT = re.compile(rf"\b(?:{_CODES})\b|synthetic", re.IGNORECASE)


def _bodies(rng, *, full, free, field, build, both, long_):
    """Body variations: complete, free form, template with gaps, spec-like."""
    fields = [code for code in FIELD for _ in range(field)]
    builds = [code for code in BUILD for _ in range(build)]
    rng.shuffle(fields)
    rng.shuffle(builds)
    only_field = len(fields) - both
    template = (
        [[f] for f in fields[:only_field]]
        + [[f, b] for f, b in zip(fields[only_field:], builds[:both], strict=True)]
        + [[b] for b in builds[both:]]
    )
    free_ = [[code] for code in FREE for _ in range(free)]
    return [["full"]] * full + free_ + template + [["spec_long"]] * long_


def _add(rng, bodies, code, n, fits):
    candidates = [b for b in bodies if len(b) < 3 and fits(b)]
    for body in rng.sample(candidates, n):
        body.append(code)


def _plan(prefix, rng, *, links, tags, tasks, **counts) -> list[dict]:
    bodies = [list(b) for b in _bodies(rng, **counts)]
    rng.shuffle(bodies)
    _add(rng, bodies, "links_tables", links, lambda b: b[0] not in (*FREE, "spec_long"))
    _add(rng, bodies, "tag_summary", tags, lambda b: True)
    _add(rng, bodies, "task_summary", tasks, lambda b: "tag_summary" not in b)
    areas = list(AREAS)
    rng.shuffle(areas)
    specs = []
    for i, codes in enumerate(bodies, 1):
        if "free_one_line" in codes:
            length = "short"
        elif "spec_long" in codes:
            length = "long"
        else:
            length = rng.choices(("short", "medium", "long"), weights=(3, 5, 2))[0]
        specs.append(
            {
                "id": f"{prefix}-{i:03d}",
                "variations": codes,
                "area": areas[i % len(areas)],
                "image_only_field": (
                    rng.choice(("actual", "expected"))
                    if "image_only" in codes
                    else None
                ),
                "length": length,
            }
        )
    return specs


def build_specs(seed: int = SEED) -> tuple[list[dict], list[dict]]:
    """80 train specs (each variation >= TRAIN_MIN) and 30 style-eval specs."""
    rng = random.Random(seed)
    train = _plan(
        "syn-train", rng, full=16, free=8, field=9, build=10, both=18, long_=0,
        links=10, tags=12, tasks=10,
    )  # fmt: skip
    style = _plan(
        "syn-style", rng, full=8, free=2, field=3, build=3, both=6, long_=3,
        links=3, tags=5, tasks=4,
    )  # fmt: skip
    return train, style


def coverage(specs: list[dict]) -> Counter:
    return Counter(code for spec in specs for code in spec["variations"])


def validate_records(specs: list[dict], records: list[dict]) -> None:
    """Raise if ids do not match the specs, a field is empty, or the text leaks."""
    expected = {s["id"] for s in specs}
    got = Counter(r["id"] for r in records)
    errors = []
    if missing := expected - set(got):
        errors.append(f"missing ids: {sorted(missing)}")
    if unexpected := set(got) - expected:
        errors.append(f"unexpected ids: {sorted(unexpected)}")
    if duplicates := [i for i, n in got.items() if n > 1]:
        errors.append(f"duplicate ids: {sorted(duplicates)}")
    for r in records:
        for field in ("summary", "description"):
            if not isinstance(r.get(field), str) or not r[field].strip():
                errors.append(f"empty {field} in {r['id']}")
        text = f"{r.get('summary')}\n{r.get('description')}"
        for host in _URL_HOST.findall(text):
            if not host.lower().endswith("example.com"):
                errors.append(f"foreign host {host} in {r['id']}")
        if m := _CODE_IN_TEXT.search(text):
            errors.append(f"variation code {m.group(0)!r} in {r['id']}")
    if errors:
        raise ValueError("; ".join(errors))


def main(argv: list[str]) -> None:
    command, *paths = argv
    if command == "specs":
        train, style = build_specs()
        Path(paths[0]).write_text(
            json.dumps({"train": train, "style": style}, indent=1), encoding="utf-8"
        )
        for name, specs in (("train", train), ("style", style)):
            print(name, len(specs), dict(sorted(coverage(specs).items())))
    elif command == "check":
        plan = json.loads(Path(paths[0]).read_text(encoding="utf-8"))
        lines = Path(paths[1]).read_text(encoding="utf-8").splitlines()
        validate_records(plan["train"] + plan["style"], [json.loads(x) for x in lines])
        print("ok:", len(lines), "records")
    else:
        raise SystemExit(f"unknown command {command!r}")


if __name__ == "__main__":
    main(sys.argv[1:])
