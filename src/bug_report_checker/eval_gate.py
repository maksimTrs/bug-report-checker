"""CI eval gate: the bot on the frozen eval set, checked against a committed baseline.

A fixed sample of `SAMPLE_SIZE` short reports (up to `MAX_CHARS` after preprocessing),
so the job stays a few minutes long: on 4 CPU threads the model takes ~6 s for a
short report and 30-40 s for ~1,000 tokens; the whole set takes about an hour. The very
shortest reports lack nearly everything, so a length cut alone would leave the gate
blind to "present"; the sample is drawn from all short ones. Long reports, read in
windows, are left to the unit tests of `decide`.

`predict` runs the model and records its raw answers; `gate` replays them through the
decision code and the config defaults (threshold, rules), so a baseline can be
rebuilt from a CI run's predictions without the model.

Two checks, two baselines in `eval/baseline/`:
- `model.json`, the raw model in laya's report format, for `laya-evals compare`;
- `bot.json`, what the bot says per check, in reports: decided, wrong among decided,
  missing parts found. `MAX_FLIPS` reports worse on any of them fails the gate; at
  this size one report is 3-7 points, so percentages would either fail on one flip or
  miss a real change.

An intended change (new model, new threshold) refreshes both with `--update`.

Usage:
  python -m bug_report_checker.eval_gate predict <eval.jsonl> <predictions.jsonl>
  python -m bug_report_checker.eval_gate gate <eval.jsonl> <predictions.jsonl>
         <baseline dir> <out dir> [--update]
"""

import json
import random
import sys
from pathlib import Path

import yaml

from bug_report_checker.config import Config
from bug_report_checker.decide import MISSING, PRESENT, UNSURE, decide
from bug_report_checker.labeling import CHECKS
from bug_report_checker.preprocess import preprocess
from bug_report_checker.questions import laya_questions

MAX_CHARS = 500  # 96 of eval v2's 170 reports
SAMPLE_SIZE = 40
SEED = 20261009
# Metric -> +1 if more is better, -1 if fewer is better.
WATCHED = {"decided": 1, "wrong": -1, "missing_found": 1}
MAX_FLIPS = 2  # one changed answer passes, two fail


def model_ref(action_yml: Path = Path("action.yml")) -> tuple[str, str]:
    """The model the Action ships: the gate tests the same pinned revision."""
    inputs = yaml.safe_load(action_yml.read_text("utf-8"))["inputs"]
    return inputs["model"]["default"], inputs["model-revision"]["default"]


def _state(row: dict) -> dict[str, str]:
    return preprocess(row["summary"], row["description"])


def _key(state: dict[str, str]) -> tuple[str, str]:
    return state["summary"], state["description"]


def gate_rows(rows: list[dict]) -> list[dict]:
    """The reports the gate runs on: a fixed sample of the short ones, in file order."""
    short = [r for r in rows if sum(map(len, _key(_state(r)))) <= MAX_CHARS]
    sample = random.Random(SEED).sample(short, min(SAMPLE_SIZE, len(short)))
    picked = {r["id"] for r in sample}
    return [r for r in short if r["id"] in picked]


def predict(agent, rows: list[dict]) -> list[dict]:
    """Raw answers per report, read exactly as the Action reads an issue."""
    out = []
    for n, row in enumerate(rows, 1):
        result = agent.predict_long(_state(row), laya_questions())
        out.append(
            {
                "id": row["id"],
                "answers": result["answers"],
                "windows": result["usage"]["windows"],
            }
        )
        if n % 10 == 0:
            print(f"{n}/{len(rows)}", flush=True)
    return out


class Replay:
    """Stands in for the model with the answers `predict` recorded.

    `predict_long` serves `decide`, `predict` serves laya's `evaluate`.
    """

    def __init__(self, rows: list[dict], predictions: list[dict]):
        by_id = {p["id"]: p for p in predictions}
        self._results = {_key(_state(r)): by_id[r["id"]] for r in rows}

    def predict_long(self, state: dict[str, str], questions: dict) -> dict:
        p = self._results[_key(state)]
        return {"answers": p["answers"], "usage": {"windows": p["windows"]}}

    def predict(self, state: dict[str, str], questions: dict, model=None) -> dict:
        return self.predict_long(state, questions)


def model_report(rows: list[dict], replay: Replay) -> dict:
    """The raw model in laya's report format; P(true) is cut at 0.5 there."""
    from laya.evals import Dataset, Example, evaluate

    examples = [
        Example(
            state=_state(r),
            questions=laya_questions(),
            expected={c: r[c] for c in CHECKS},
            tags=("core" if r["core"] else "added",),
        )
        for r in rows
    ]
    return evaluate(replay, Dataset(examples)).to_json()


def bot_metrics(rows: list[dict], replay: Replay, config: Config) -> dict[str, dict]:
    """What the bot says per check, rules and the "not sure" band included."""
    verdicts = [decide(replay, _state(r), config).verdicts for r in rows]
    out = {}
    for check in CHECKS:
        pairs = [(r[check], v[check]) for r, v in zip(rows, verdicts, strict=True)]
        decided = [(g, v) for g, v in pairs if v != UNSURE]
        out[check] = {
            "n": len(pairs),
            "decided": len(decided),
            "wrong": sum((v == PRESENT) != g for g, v in decided),
            "missing_n": sum(not g for g, _ in pairs),
            "missing_found": sum(not g and v == MISSING for g, v in pairs),
            "false_missing": sum(g and v == MISSING for g, v in pairs),
        }
    return out


def regressions(now: dict[str, dict], baseline: dict[str, dict]) -> list[str]:
    """A watched count `MAX_FLIPS` or more reports worse than the baseline."""
    reasons = []
    for check, base in baseline.items():
        for metric, sign in WATCHED.items():
            was, value = base[metric], now[check][metric]
            if sign * (was - value) >= MAX_FLIPS:
                reasons.append(f"{check}: {metric} {was} -> {value}")
    return reasons


def summary(now: dict[str, dict], baseline: dict[str, dict], reasons: list[str]) -> str:
    """Markdown for the job summary: one row per check, baseline → now."""
    failed = {r.split(":", 1)[0] for r in reasons}
    lines = [
        "## Bot on eval v2, short reports",
        "",
        f"{SAMPLE_SIZE} reports up to {MAX_CHARS} characters, threshold"
        f" {Config().threshold}; {MAX_FLIPS} reports worse in any column fails.",
        "",
        "| Check | Decided | Wrong | Missing found | |",
        "|---|---|---|---|---|",
    ]
    for check, base in baseline.items():
        b, n = base, now[check]
        mark = "❌" if check in failed else "✅"
        lines.append(
            f"| {check} | {b['decided']} → {n['decided']} | {b['wrong']} → {n['wrong']}"
            f" | {b['missing_found']} → {n['missing_found']} of {b['missing_n']}"
            f" | {mark} |"
        )
    lines.append("")
    if reasons:
        lines += ["**Regression:**", "", *(f"- {r}" for r in reasons), ""]
        lines.append(
            "Intended? Refresh `eval/baseline/` with `eval_gate gate ... --update`."
        )
    return "\n".join(lines) + "\n"


def _read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines()]


def _write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=1) + "\n", "utf-8", newline="\n")


def main(argv: list[str]) -> None:
    if argv[0] == "predict":
        import laya

        model, revision = model_ref()
        print(f"{model}@{revision}", flush=True)
        agent = laya.load(model, device="cpu", revision=revision)
        preds = predict(agent, gate_rows(_read(Path(argv[1]))))
        with open(argv[2], "w", encoding="utf-8", newline="\n") as f:
            f.writelines(json.dumps(p) + "\n" for p in preds)
    elif argv[0] == "gate":
        rows, preds = gate_rows(_read(Path(argv[1]))), _read(Path(argv[2]))
        base_dir, out = Path(argv[3]), Path(argv[4])
        replay = Replay(rows, preds)
        report = model_report(rows, replay)
        bot = bot_metrics(rows, replay, Config())
        out.mkdir(parents=True, exist_ok=True)
        _write(out / "report.json", report)
        _write(out / "bot.json", bot)
        if "--update" in argv:
            base_dir.mkdir(parents=True, exist_ok=True)
            _write(
                base_dir / "model.json", {k: report[k] for k in report if k != "cases"}
            )
            _write(base_dir / "bot.json", bot)
            print(f"baseline written to {base_dir}")
            return
        baseline = json.loads((base_dir / "bot.json").read_text("utf-8"))
        reasons = regressions(bot, baseline)
        md = summary(bot, baseline, reasons)
        (out / "summary.md").write_text(md, "utf-8", newline="\n")
        print("\n".join(reasons) or "pass")  # the markdown is for the job summary
        if reasons:
            raise SystemExit(1)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
