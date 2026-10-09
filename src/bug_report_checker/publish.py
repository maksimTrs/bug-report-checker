"""The bot keeps one comment per issue and updates it on every re-check.

Its comment ends with an HTML-comment marker holding a fingerprint of what the
check read. An event that changed none of it (another label, an assignee) is
skipped before the model runs; bursts of edits are collapsed by the workflow's
`concurrency`, so a fix right after the bot's comment is never left unchecked.
"""

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import asdict

import httpx

from bug_report_checker.config import Config

MARKER = "<!-- bug-report-checker fingerprint={} -->"
_FINGERPRINT = re.compile(r"<!-- bug-report-checker fingerprint=(\w+) -->\s*\Z")
PER_PAGE = 100  # the REST API maximum

CREATED, UPDATED, SKIPPED, SILENT = "created", "updated", "skipped", "silent"


def fingerprint(state: dict[str, str], status: str, config: Config) -> str:
    """Everything the comment depends on: the text, the status, the settings."""
    data = json.dumps([state, status, asdict(config)], sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:16]


class Comments:
    """Comments of one issue through the GitHub REST API."""

    def __init__(self, client: httpx.Client, repo: str, issue_number: int):
        self.client = client
        self.path = f"/repos/{repo}/issues"
        self.issue_number = issue_number

    def own(self) -> dict | None:
        """The bot's comment, found by its marker on any page."""
        page = 1
        while True:
            r = self.client.get(
                f"{self.path}/{self.issue_number}/comments",
                params={"per_page": PER_PAGE, "page": page},
            )
            r.raise_for_status()
            batch = r.json()
            for comment in batch:
                if _FINGERPRINT.search(comment["body"] or ""):
                    return comment
            if len(batch) < PER_PAGE:
                return None
            page += 1

    def create(self, body: str) -> None:
        r = self.client.post(
            f"{self.path}/{self.issue_number}/comments", json={"body": body}
        )
        r.raise_for_status()

    def update(self, comment_id: int, body: str) -> None:
        r = self.client.patch(f"{self.path}/comments/{comment_id}", json={"body": body})
        r.raise_for_status()


def run_check(
    comments: Comments,
    fp: str,
    make_body: Callable[[], tuple[str, bool]],
    *,
    comment_on_success: bool,
) -> str:
    """`make_body` runs the model and returns the comment and whether the report is
    complete. A complete report gets no new comment when the team asked for
    silence, but an existing one is still updated, so no stale "missing" stays."""
    own = comments.own()
    if own and _FINGERPRINT.search(own["body"])[1] == fp:
        return SKIPPED
    body, complete = make_body()
    stamped = f"{body}\n\n{MARKER.format(fp)}"
    if own:
        comments.update(own["id"], stamped)
        return UPDATED
    if complete and not comment_on_success:
        return SILENT
    comments.create(stamped)
    return CREATED
