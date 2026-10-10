import pytest

from bug_report_checker.config import Config
from bug_report_checker.decide import MISSING, PRESENT, UNSURE, decide
from bug_report_checker.questions import QUESTIONS, laya_questions


class FakeAgent:
    """Answers every question with one P(true), or per check from `p`."""

    def __init__(self, p=0.95, windows=1, **per_check):
        self.p = {c: per_check.get(c, p) for c in QUESTIONS}
        self.windows = windows
        self.calls = []

    def predict_long(self, state, questions):
        self.calls.append((state, questions))
        return {
            "answers": {c: {"noul": self.p[c]} for c in questions},
            "usage": {"windows": self.windows},
        }


def state(description="**Steps to reproduce:**\n1. Open", summary="Export crashes"):
    return {"summary": summary, "description": description}


CONFIG = Config(threshold=0.8)


@pytest.mark.parametrize(
    ("p", "verdict"),
    [(0.95, PRESENT), (0.8, PRESENT), (0.79, UNSURE), (0.21, UNSURE), (0.2, MISSING)],
)
def test_threshold_splits_present_missing_unsure(p, verdict):
    d = decide(FakeAgent(p), state(), CONFIG)
    assert d.verdicts["summary_what"] == verdict


def test_model_gets_the_state_and_the_trained_questions():
    agent = FakeAgent()
    decide(agent, state(), CONFIG)
    assert agent.calls == [(state(), laya_questions())]


def test_every_check_gets_a_verdict():
    assert set(decide(FakeAgent(), state(), CONFIG).verdicts) == set(QUESTIONS)


def test_empty_description_means_no_steps_whatever_the_model_says():
    d = decide(FakeAgent(0.99), state(""), CONFIG)
    assert d.verdicts["steps"] == MISSING
    # The summary still counts for the rest (rubric): the model decides them.
    assert d.verdicts["expected"] == PRESENT


@pytest.mark.parametrize(
    ("description", "p", "verdict"),
    [
        ("**Build version:** R26.03-412", 0.1, PRESENT),  # team format beats model
        ("**Build version:** current prod", 0.99, MISSING),  # vague beats model
        ("**Build version:** 4.18.2", 0.99, PRESENT),  # code unsure: model
        ("**Build version:** 4.18.2", 0.5, UNSURE),
    ],
)
def test_build_version_code_first_then_model(description, p, verdict):
    config = Config(threshold=0.8, build_version_pattern=r"\bR\d{2}\.\d{2}-\d+\b")
    d = decide(FakeAgent(build_version=p), state(description), config)
    assert d.verdicts["build_version"] == verdict


@pytest.mark.parametrize(("windows", "long"), [(1, False), (3, True)])
def test_long_report_is_flagged(windows, long):
    assert decide(FakeAgent(windows=windows), state(), CONFIG).long is long


def test_long_report_present_blockers_become_unsure():
    # The max over windows drifts towards "present"; only "missing" is trusted.
    d = decide(FakeAgent(0.95, windows=3, actual=0.05), state(), CONFIG)
    assert d.verdicts == {
        "summary_what": PRESENT,  # the summary is in the first window
        "summary_where": PRESENT,
        "summary_when": PRESENT,
        "steps": UNSURE,
        "expected": UNSURE,
        "actual": MISSING,
        "build_version": UNSURE,
    }


def test_long_report_keeps_a_build_found_by_code():
    config = Config(threshold=0.8, build_version_pattern=r"\bR\d{2}\.\d{2}-\d+\b")
    d = decide(FakeAgent(0.95, windows=3), state("Build R26.03-412"), config)
    assert d.verdicts["build_version"] == PRESENT


def test_empty_template_sections_are_missing_whatever_the_model_says():
    # Seen live: the model read a bare "Steps to reproduce" heading as steps.
    description = (
        "### Steps to reproduce\n\n### Actual result\n\nBlank page\n\n"
        "### Expected result\n\nTBD"
    )
    d = decide(FakeAgent(0.99), state(description), CONFIG)
    assert (d.verdicts["steps"], d.verdicts["expected"]) == (MISSING, MISSING)
    assert d.verdicts["actual"] == PRESENT


def test_environment_and_image_only_come_from_code():
    description = "Seen on qa1 and prod\n**Actual result:**\n[image]"
    d = decide(FakeAgent(), state(description), Config(environments=("qa1",)))
    assert (d.environments, d.image_only) == (["qa1", "prod"], ["actual"])


SANDBOX_8 = state(
    "When I try to export pdf, I can see red errors on UI page",
    "Invoice PDF export fails from time to time",
)
STRICT = Config(threshold=0.8, strict=True)


def test_strict_off_by_default_keeps_the_model_verdicts():
    d = decide(FakeAgent(0.95), SANDBOX_8, CONFIG)
    assert d.verdicts["expected"] == d.verdicts["actual"] == PRESENT
    assert d.strict is False


def test_strict_lowers_what_the_description_does_not_state():
    d = decide(FakeAgent(0.95), SANDBOX_8, STRICT)
    assert [d.verdicts[c] for c in ("steps", "expected", "actual")] == [MISSING] * 3
    assert d.strict is True


def test_strict_lowers_unsure_too():
    d = decide(FakeAgent(0.5), SANDBOX_8, STRICT)
    assert d.verdicts["actual"] == MISSING


def test_strict_never_raises_a_missing_verdict():
    complete = state(
        "1. Open Invoices\n2. Click Export PDF\n\n"
        'Expected: the PDF downloads.\n\nActual: "Export failed: timeout".'
    )
    d = decide(FakeAgent(0.95, steps=0.05), complete, STRICT)
    assert d.verdicts["steps"] == MISSING
    assert d.verdicts["expected"] == d.verdicts["actual"] == PRESENT
