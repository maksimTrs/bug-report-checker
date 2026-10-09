"""Core: decides on a tracker-neutral `Issue`, never on tracker fields."""

from bug_report_checker.issue import BUG, Issue

# YouTrack's default states while a bug is filed or just taken; a team with its own
# workflow lists its states in the config.
TRIGGER_STATES = ("Submitted", "Open", "In Progress")


def should_check(issue: Issue, states: tuple[str, ...] = TRIGGER_STATES) -> bool:
    """Only bugs in a trigger state; a closed issue has no state."""
    return issue.type == BUG and issue.state in states
