import json

import httpx
import pytest

from bug_report_checker.config import Config
from bug_report_checker.publish import (
    CREATED,
    SILENT,
    SKIPPED,
    UPDATED,
    Comments,
    fingerprint,
    run_check,
)

STATE = {"summary": "Export crashes", "description": "1. Open"}
FP = fingerprint(STATE, "Open", Config())


class FakeGitHub:
    """Issue comments of one issue, served the way the REST API pages them."""

    def __init__(self, bodies=()):
        self.comments = [{"id": i + 1, "body": b} for i, b in enumerate(bodies)]
        self.requests = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append((request.method, request.url.path))
        if request.method == "GET":
            page = int(request.url.params["page"])
            per_page = int(request.url.params["per_page"])
            chunk = self.comments[(page - 1) * per_page : page * per_page]
            return httpx.Response(200, json=chunk)
        body = json.loads(request.content)["body"]
        if request.method == "POST":
            self.comments.append({"id": len(self.comments) + 1, "body": body})
            return httpx.Response(201, json=self.comments[-1])
        comment_id = int(request.url.path.rsplit("/", 1)[1])
        self.comments[comment_id - 1]["body"] = body
        return httpx.Response(200, json=self.comments[comment_id - 1])


def comments(server):
    client = httpx.Client(
        base_url="https://api.github.com", transport=httpx.MockTransport(server)
    )
    return Comments(client, "octo/app", 7)


def body(complete=False, text="Missing: steps"):
    return lambda: (text, complete)


def test_first_check_creates_a_comment_with_a_marker():
    server = FakeGitHub(["A human comment"])
    assert run_check(comments(server), FP, body(), comment_on_success=True) == CREATED
    assert server.requests[-1] == ("POST", "/repos/octo/app/issues/7/comments")
    assert server.comments[-1]["body"].startswith("Missing: steps\n\n<!-- bug-report")
    assert FP in server.comments[-1]["body"]


def test_recheck_updates_own_comment_instead_of_a_new_one():
    old = "Missing: steps\n\n<!-- bug-report-checker fingerprint=0000 -->"
    server = FakeGitHub(["A human comment", old])
    complete = body(True, "Complete")
    assert run_check(comments(server), FP, complete, comment_on_success=False) == (
        UPDATED
    )
    assert server.requests[-1] == ("PATCH", "/repos/octo/app/issues/comments/2")
    assert len(server.comments) == 2
    assert server.comments[1]["body"].startswith("Complete")


def test_unchanged_report_is_skipped_without_running_the_model():
    server = FakeGitHub(
        [f"Missing: steps\n\n<!-- bug-report-checker fingerprint={FP} -->"]
    )
    calls = []

    def make_body():
        calls.append(1)
        return "x", False

    assert run_check(comments(server), FP, make_body, comment_on_success=True) == (
        SKIPPED
    )
    assert calls == []
    assert [m for m, _ in server.requests] == ["GET"]


def test_complete_report_stays_silent_when_configured_and_no_comment_yet():
    server = FakeGitHub()
    assert run_check(comments(server), FP, body(True), comment_on_success=False) == (
        SILENT
    )
    assert server.comments == []


def test_own_comment_is_found_past_the_first_page():
    bodies = [f"human {i}" for i in range(100)]
    bodies.append("old\n\n<!-- bug-report-checker fingerprint=0000 -->")
    server = FakeGitHub(bodies)
    assert run_check(comments(server), FP, body(), comment_on_success=True) == UPDATED
    assert server.requests[-1] == ("PATCH", "/repos/octo/app/issues/comments/101")


@pytest.mark.parametrize(
    "change",
    [
        lambda s, st, c: ({**s, "description": "1. Open\n2. Save"}, st, c),
        lambda s, st, c: (s, "In Progress", c),
        lambda s, st, c: (s, st, Config(threshold=0.9)),
    ],
)
def test_fingerprint_changes_with_text_status_and_config(change):
    assert fingerprint(*change(STATE, "Open", Config())) != FP


def test_api_error_is_raised():
    def server(request):
        return httpx.Response(403, json={"message": "Resource not accessible"})

    with pytest.raises(httpx.HTTPStatusError):
        run_check(comments(server), FP, body(), comment_on_success=True)
