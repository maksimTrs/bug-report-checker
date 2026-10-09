"""Decision on a preprocessed report: the model answers, code overrides where exact.

The agent is anything with Laya's `predict_long`; tests pass a fake one.
"""

from dataclasses import dataclass

from bug_report_checker.config import Config
from bug_report_checker.questions import laya_questions
from bug_report_checker.rules import build_version, environment, image_only

PRESENT = "present"
MISSING = "missing"
UNSURE = "unsure"
BLOCKERS = ("steps", "expected", "actual", "build_version")  # the rest are hints


@dataclass(frozen=True)
class Decision:
    verdicts: dict[str, str]  # check -> PRESENT / MISSING / UNSURE
    long: bool  # read in several windows: the answers are less reliable
    environments: list[str]
    image_only: list[str]  # result fields shown only as a screenshot


def _verdict(p_true: float, threshold: float) -> str:
    """Below `threshold` confidence the bot gives no verdict (calibrated, T3.4)."""
    if max(p_true, 1 - p_true) < threshold:
        return UNSURE
    return PRESENT if p_true >= 0.5 else MISSING


def decide(agent, state: dict[str, str], config: Config) -> Decision:
    """`predict_long` reads a report that fits in one pass exactly as `predict`
    does, and a longer one in overlapping windows instead of cutting it off."""
    result = agent.predict_long(state, laya_questions())
    verdicts = {
        check: _verdict(answer["noul"], config.threshold)
        for check, answer in result["answers"].items()
    }
    long = result["usage"]["windows"] > 1
    if long:
        # P(true) is the max over windows and drifts up with their count: run 2 found
        # 1 of 10 missing expected / actual in long reports (decision 2026-10-09).
        for check in BLOCKERS:
            if verdicts[check] == PRESENT:
                verdicts[check] = UNSURE
    if not state["description"]:
        verdicts["steps"] = MISSING  # the summary is never the steps (rubric)
    build = build_version(state, config.build_version_pattern)
    if build is not None:
        verdicts["build_version"] = PRESENT if build else MISSING
    return Decision(
        verdicts=verdicts,
        long=long,
        environments=environment(state, config.environments),
        image_only=image_only(state),
    )
