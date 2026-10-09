"""A tracker-neutral issue: the core decides on these four fields only.

Each tracker gets an adapter that maps its own fields here, so moving to another
tracker needs a new adapter, not a retrained model.
"""

from dataclasses import dataclass

BUG = "bug"
OTHER = "other"


@dataclass(frozen=True)
class Issue:
    type: str  # BUG or OTHER: the tracker says what a bug is, not the model
    state: str | None  # the tracker's status name; None when the issue is closed
    summary: str
    description: str
