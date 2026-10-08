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
from pathlib import Path

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
    return [json.loads(line) for line in text.splitlines() if line.strip()]


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
        raw = raw_dir / f"batch_{n:02d}.json"
        if raw.exists():  # resume: a finished batch is not asked again
            answer = json.loads(raw.read_text("utf-8"))
        else:
            answer = ask(batch_input(rows[start : start + size]), model, prompt_file)
            raw.write_text(json.dumps(answer, ensure_ascii=False), encoding="utf-8")
        labels += parse_answer(answer["result"])
        models |= answer.get("modelUsage", {}).keys()
        print(f"batch {n}: {len(labels)} labels so far", flush=True)

    with open(out_dir / "labels.jsonl", "w", encoding="utf-8", newline="\n") as out:
        out.writelines(json.dumps(r) + "\n" for r in labels)
    print("models:", sorted(models))


if __name__ == "__main__":
    main(sys.argv[1:])
