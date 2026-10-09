import pytest

from bug_report_checker.core import TRIGGER_STATES, should_check
from bug_report_checker.issue import BUG, OTHER, Issue


def issue(type_=BUG, state="Open"):
    return Issue(type_, state, "Crash on save", "Steps")


@pytest.mark.parametrize("state", ["Submitted", "Open", "Opened", "In Progress"])
def test_bug_in_a_trigger_state_is_checked(state):
    assert state in TRIGGER_STATES
    assert should_check(issue(state=state))


@pytest.mark.parametrize(
    "state",
    ["On-hold", "In Clarification", "Ready for Verification", "Reviewing", None],
)
def test_bug_in_another_state_or_closed_is_skipped(state):
    assert not should_check(issue(state=state))


def test_non_bug_is_skipped_in_any_state():
    assert not should_check(issue(type_=OTHER, state="Open"))
