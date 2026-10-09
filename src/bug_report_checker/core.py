"""Core: decides on a tracker-neutral `Issue`, never on tracker fields."""

from bug_report_checker.issue import BUG, Issue

# Statuses where a bug is still being filed or just taken; later ones (On-hold,
# In Clarification, Ready for Verification, ...) are past the point of checking it.
TRIGGER_STATES = ("Submitted", "Open", "Opened", "In Progress")


def should_check(issue: Issue) -> bool:
    """Only bugs in a trigger state; a closed issue has no state."""
    return issue.type == BUG and issue.state in TRIGGER_STATES
