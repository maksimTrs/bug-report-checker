import json

import pytest

from bug_report_checker import eval_gate
from bug_report_checker.config import Config
from bug_report_checker.labeling import CHECKS


def row(rid, description="Clicking Save shows an error.", core=True, **missing):
    """An eval row; every check present unless named False."""
    return {
        "id": rid,
        "summary": f"Save fails {rid}",
        "description": description,
        "core": core,
        **{c: missing.get(c, True) for c in CHECKS},
    }


def answers(p=0.95, windows=1, **per_check):
    """What `predict` records for one report: Laya's answer dicts and the windows."""
    ps = {c: per_check.get(c, p) for c in CHECKS}
    return {
        "answers": {
            c: {"type": "noul", "noul": v, "answer_confidence": max(v, 1 - v)}
            for c, v in ps.items()
        },
        "windows": windows,
    }


ROWS = [row("A"), row("B", expected=False), row("C", expected=False)]
PREDS = [
    {"id": "A", **answers()},
    {"id": "B", **answers(expected=0.1)},  # missing, found
    {"id": "C", **answers(expected=0.7)},  # missing, but not sure at 0.827
]


class FakeAgent:
    def __init__(self, preds):
        self.preds = iter(preds)
        self.states = []

    def predict_long(self, state, questions):
        self.states.append(state)
        p = next(self.preds)
        return {"answers": p["answers"], "usage": {"windows": p["windows"]}}


def test_model_ref_reads_the_pinned_model_from_action_yml():
    model, revision = eval_gate.model_ref()
    assert model == "ippo123/bug-report-checker"
    assert len(revision) == 40


def test_predict_records_answers_and_windows_of_the_preprocessed_state():
    rows = [row("A", description="See http://x.org/a for details.")]
    agent = FakeAgent([answers(windows=2)])
    preds = eval_gate.predict(agent, rows)
    assert preds == [{"id": "A", **answers(windows=2)}]
    assert agent.states[0]["description"] == "See [link: x.org] for details."


def test_bot_metrics_follow_the_decision_code():
    replay = eval_gate.Replay(ROWS, PREDS)
    m = eval_gate.bot_metrics(ROWS, replay, Config())["expected"]
    assert m == {
        "n": 3,
        "decided": 2,  # C is "not sure" at 0.827
        "wrong": 0,
        "missing_n": 2,
        "missing_found": 1,
        "false_missing": 0,
    }


def test_bot_metrics_see_a_lower_threshold():
    replay = eval_gate.Replay(ROWS, PREDS)
    m = eval_gate.bot_metrics(ROWS, replay, Config(threshold=0.65))["expected"]
    assert m["decided"] == 3
    assert m["wrong"] == 1  # C decided as "present"


def test_bot_metrics_apply_the_rules():
    rows = [row("A", description="**Steps to reproduce:**\n\n**Actual:** error")]
    m = eval_gate.bot_metrics(rows, eval_gate.Replay(rows, PREDS[:1]), Config())
    assert m["steps"]["false_missing"] == 1  # empty Steps heading beats the model


def test_gate_rows_keep_short_reports_after_preprocessing():
    short = row("A", description="x" * 400)
    long = row("B", description="x" * 500)
    linked = row("C", description="x" * 450 + " https://example.org/a/very/long/path")
    assert [r["id"] for r in eval_gate.gate_rows([short, long, linked])] == ["A", "C"]


def test_gate_rows_sample_is_fixed_and_in_file_order():
    rows = [row(f"R{i:03}") for i in range(100)]
    picked = eval_gate.gate_rows(rows)
    assert len(picked) == eval_gate.SAMPLE_SIZE
    assert picked == eval_gate.gate_rows(rows)
    assert [r["id"] for r in picked] == sorted(r["id"] for r in picked)


def test_replay_refuses_predictions_for_another_set():
    with pytest.raises(KeyError):
        eval_gate.Replay([row("Z")], PREDS)


def test_model_report_scores_every_answer_in_laya_format():
    report = eval_gate.model_report(ROWS, eval_gate.Replay(ROWS, PREDS))
    assert len(report["cases"]) == 3 * len(CHECKS)
    # wrong only on C.expected: 0.7 says "present"
    assert report["overall"]["noul_accuracy"] == pytest.approx(20 / 21)
    assert report["slices"]["qid"]["expected"]["noul_accuracy"] == pytest.approx(2 / 3)
    assert set(report["slices"]["tag"]) == {"core"}


def metrics(**values):
    base = {"n": 40, "decided": 30, "wrong": 3, "missing_n": 20, "missing_found": 15}
    return {"expected": {**base, **values}}


@pytest.mark.parametrize(
    "now",
    [
        metrics(),
        metrics(decided=29, wrong=4, missing_found=14),  # one report each: noise
        metrics(decided=35, wrong=0),  # better is not a regression
    ],
)
def test_no_regression_below_two_reports(now):
    assert eval_gate.regressions(now, metrics()) == []


@pytest.mark.parametrize(
    ("now", "reason"),
    [
        (metrics(decided=28), "expected: decided 30 -> 28"),
        (metrics(wrong=5), "expected: wrong 3 -> 5"),
        (metrics(missing_found=13), "expected: missing_found 15 -> 13"),
    ],
)
def test_two_reports_worse_is_a_regression(now, reason):
    assert eval_gate.regressions(now, metrics()) == [reason]


def test_summary_marks_the_failing_check():
    md = eval_gate.summary(metrics(decided=20), metrics(), ["expected: decided"])
    assert "| expected | 30 → 20 | 3 → 3 | 15 → 15 of 20 | ❌ |" in md
    assert "- expected: decided" in md


def test_gate_writes_reports_and_fails_on_regression(tmp_path):
    eval_path = tmp_path / "eval.jsonl"
    preds_path = tmp_path / "preds.jsonl"
    eval_path.write_text("".join(json.dumps(r) + "\n" for r in ROWS), "utf-8")
    preds_path.write_text("".join(json.dumps(p) + "\n" for p in PREDS), "utf-8")
    base, out = tmp_path / "baseline", tmp_path / "out"
    args = [str(eval_path), str(preds_path), str(base), str(out)]

    eval_gate.main(["gate", *args, "--update"])
    assert "cases" not in json.loads((base / "model.json").read_text("utf-8"))
    eval_gate.main(["gate", *args])  # same predictions: pass
    assert "✅" in (out / "summary.md").read_text("utf-8")

    # B: found → called present; C: not sure → called present. Two wrong answers.
    worse = [
        PREDS[0],
        {"id": "B", **answers(expected=0.9)},
        {"id": "C", **answers(expected=0.9)},
    ]
    preds_path.write_text("".join(json.dumps(p) + "\n" for p in worse), "utf-8")
    with pytest.raises(SystemExit) as e:
        eval_gate.main(["gate", *args])
    assert e.value.code == 1
    assert json.loads((out / "report.json").read_text("utf-8"))["cases"]
