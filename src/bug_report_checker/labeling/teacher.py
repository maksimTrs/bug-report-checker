"""Label bug reports with a Claude teacher through headless Claude Code.

Each batch goes to `claude -p` with the prompt and rubric as the system prompt,
no tools and no user settings, so the teacher sees only the rubric and the
reports. The full CLI answer of every batch is kept in <out_dir>/raw/: it holds
the exact model id (modelUsage) and lets an interrupted run resume.

Usage: python -m bug_report_checker.labeling.teacher <reports.jsonl> <out_dir>
       <model> [batch_size]
"""

import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

from bug_report_checker.labeling import CHECKS

LABELING_DIR = Path(__file__).parents[3] / "labeling"
BATCH_SIZE = 20


def system_prompt(labeling_dir: Path = LABELING_DIR) -> str:
    prompt = (labeling_dir / "prompt.md").read_text("utf-8")
    rubric = (labeling_dir / "rubric.md").read_text("utf-8")
    return prompt + "\n" + rubric


def batch_input(rows: list[dict]) -> str:
    """Only the id and the text: source, tracker and project must not sway labels."""
    return "".join(
        json.dumps(
            {k: r[k] for k in ("id", "summary", "description")}, ensure_ascii=False
        )
        + "\n"
        for r in rows
    )


def parse_answer(text: str) -> list[dict]:
    rows = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"line {n}: not JSON ({e.msg}): {line[:80]}") from e
        if not isinstance(row, dict):
            raise ValueError(f"line {n}: not a JSON object: {line[:80]}")
        rows.append(row)
    return rows


def check_labels(rows: list[dict], ids: list[str]) -> None:
    """Raise on any problem: keys, value types, missing / foreign / repeated ids."""
    errors = []
    keys = {"id", *CHECKS}
    for r in rows:
        name = r.get("id")
        if missing := keys - r.keys():
            errors.append(f"{name}: missing keys {sorted(missing)}")
        if extra := r.keys() - keys:
            errors.append(f"{name}: extra keys {sorted(extra)}")
        errors += [
            f"{name}: {c} is not true/false"
            for c in CHECKS
            if c in r and not isinstance(r[c], bool)
        ]
    got = Counter(r.get("id") for r in rows)
    if missing := [i for i in ids if i not in got]:
        errors.append(f"missing ids {missing}")
    if unexpected := sorted(set(got) - set(ids), key=str):
        errors.append(f"unexpected ids {unexpected}")
    if duplicates := sorted(i for i, n in got.items() if n > 1 and i in ids):
        errors.append(f"duplicate ids {duplicates}")
    if errors:
        raise ValueError("; ".join(errors))


def ask(batch: str, model: str, system_prompt_file: Path) -> dict:
    claude = shutil.which("claude")
    if claude is None:
        raise RuntimeError("claude CLI not found on PATH")
    done = subprocess.run(
        [
            claude,
            "-p",
            "--model",
            model,
            "--tools",
            "",
            "--setting-sources",
            "",
            "--no-session-persistence",
            "--system-prompt-file",
            str(system_prompt_file),
            "--output-format",
            "json",
        ],
        input=batch,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    answer = json.loads(done.stdout)
    if answer.get("is_error"):
        raise RuntimeError(f"claude returned an error: {answer.get('result')}")
    return answer


def main(argv: list[str]) -> None:
    reports, out_dir, model = Path(argv[0]), Path(argv[1]), argv[2]
    size = int(argv[3]) if len(argv) > 3 else BATCH_SIZE
    rows = [json.loads(line) for line in reports.read_text("utf-8").splitlines()]
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = out_dir / "system_prompt.md"
    prompt_file.write_text(system_prompt(), encoding="utf-8")

    labels, models = [], set()
    for n, start in enumerate(range(0, len(rows), size), 1):
        batch = rows[start : start + size]
        raw = raw_dir / f"batch_{n:02d}.json"
        if raw.exists():  # resume: a finished batch is not asked again
            answer = json.loads(raw.read_text("utf-8"))
        else:
            answer = ask(batch_input(batch), model, prompt_file)
        text = json.dumps(answer, ensure_ascii=False)
        try:
            got = parse_answer(answer["result"])
            check_labels(got, [r["id"] for r in batch])
        except ValueError as e:
            # Kept for inspection; without a valid raw file the batch is asked again.
            raw.with_suffix(".invalid.json").write_text(text, encoding="utf-8")
            raise ValueError(f"batch {n}: {e}") from e
        raw.write_text(text, encoding="utf-8")
        labels += got
        models |= answer.get("modelUsage", {}).keys()
        print(f"batch {n}: {len(labels)} labels so far", flush=True)

    check_labels(labels, [r["id"] for r in rows])
    with open(out_dir / "labels.jsonl", "w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(r) + "\n" for r in labels)
    print("models:", sorted(models))


if __name__ == "__main__":
    main(sys.argv[1:])
