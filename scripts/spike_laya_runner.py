"""T0.6 spike: Laya `typed-decisions` on a GitHub-hosted CPU runner.

Measures checkpoint download, load, latency and peak RSS; writes a Markdown table
to $GITHUB_STEP_SUMMARY. Linux only (uses `resource`). Throwaway: removed once
T0.6 is recorded.
"""

import os
import resource
import time

import laya
from huggingface_hub import snapshot_download

REPO, SUBFOLDER = "convaiinnovations/laya", "typed-decisions"
QUESTIONS = {
    "steps": {
        "type": "noul",
        "instructions": "Does the bug report contain steps to reproduce?",
    },
    "expected": {
        "type": "noul",
        "instructions": "Does the bug report state the expected result?",
    },
}
SHORT_BUG = """Build version: 2026.09-dev-118
Steps to reproduce:
1. Open the Invoices screen.
2. Click Export to CSV.
Actual result: the app shows a blank page.
Expected result: a CSV file is downloaded."""
FILLER = "\n".join(
    f"{i}. Open the Settings page and toggle option number {i} twice."
    for i in range(3, 62)
)
LONG_BUG = SHORT_BUG.replace(
    "2. Click Export to CSV.", FILLER + "\n62. Click Export to CSV."
)


def peak_rss_mb() -> float:
    # Linux reports ru_maxrss in KiB.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def median_ms(agent: laya.Agent, state: str, runs: int) -> float:
    agent.predict(state, QUESTIONS, max_len=1024, head_max_len=256)  # warm-up
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        agent.predict(state, QUESTIONS, max_len=1024, head_max_len=256)
        times.append(time.perf_counter() - t0)
    return sorted(times)[runs // 2] * 1000


def main() -> None:
    t0 = time.perf_counter()
    snapshot_download(REPO, allow_patterns=[f"{SUBFOLDER}/*"])
    download_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    agent = laya.load(REPO, subfolder=SUBFOLDER, device="cpu")
    load_s = time.perf_counter() - t0

    long_tokens = len(agent.tok(LONG_BUG)["input_ids"])
    rows = [
        ("CPUs", os.cpu_count()),
        ("Checkpoint download", f"{download_s:.1f} s"),
        ("Load", f"{load_s:.1f} s"),
        ("Short bug, median of 5", f"{median_ms(agent, SHORT_BUG, 5):.0f} ms"),
        (
            f"Long bug ({long_tokens} tok), median of 3",
            f"{median_ms(agent, LONG_BUG, 3):.0f} ms",
        ),
        ("Peak RSS", f"{peak_rss_mb():.0f} MB"),
    ]
    table = "| Metric | Value |\n|---|---|\n" + "\n".join(
        f"| {k} | {v} |" for k, v in rows
    )
    print(table)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("## Laya typed-decisions on CPU runner\n\n" + table + "\n")


if __name__ == "__main__":
    main()
