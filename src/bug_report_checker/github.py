"""GitHub adapter: an issue object from an `issues` webhook event -> `Issue`.

GitHub has no workflow statuses, so statuses are labels. An open issue without a
status label counts as just submitted, as a new issue does in YouTrack; labels
outside `status_labels` are not statuses, so they do not change that.
"""

import re

from bug_report_checker.issue import BUG, OTHER, Issue

BUG_LABELS = ("bug",)
STATUS_LABELS = ("Submitted", "Open", "Opened", "In Progress")
NEW = "Submitted"
# Issue forms write a skipped optional field as this line under the field heading.
_NO_RESPONSE = re.compile(r"^_No response_[ \t]*$", re.M)


def from_github(
    issue: dict,
    *,
    bug_labels: tuple[str, ...] = BUG_LABELS,
    status_labels: tuple[str, ...] = STATUS_LABELS,
) -> Issue:
    """Labels match case-insensitively; with several status labels the first in
    `status_labels` wins. A native issue type named Bug also makes a bug."""
    labels = {label["name"].casefold() for label in issue["labels"]}
    native = (issue.get("type") or {}).get("name", "")
    is_bug = native.casefold() == BUG or any(b.casefold() in labels for b in bug_labels)
    state = None
    if issue["state"] == "open":
        state = next((s for s in status_labels if s.casefold() in labels), NEW)
    return Issue(
        type=BUG if is_bug else OTHER,
        state=state,
        summary=issue["title"],
        description=_NO_RESPONSE.sub("", issue["body"] or ""),
    )
