import json

import httpx
import pytest

from bug_report_checker.action import run
from bug_report_checker.config import ConfigError


class FakeAgent:
    def predict_long(self, state, questions):
        return {
            "answers": {c: {"noul": 0.02 if c == "steps" else 0.98} for c in questions},
            "usage": {"windows": 1},
        }


class FakeGitHub:
    def __init__(self, config=None):
        self.config = config
        self.posted = []

    def __call__(self, request):
        path = request.url.path
        if path.endswith("/contents/.github/bug-checker.yml"):
            assert request.headers["accept"] == "application/vnd.github.raw+json"
            if self.config is None:
                return httpx.Response(404, json={"message": "Not Found"})
            return httpx.Response(200, text=self.config)
        if request.method == "GET":
            return httpx.Response(200, json=[])
        self.posted.append(json.loads(request.content)["body"])
        return httpx.Response(201, json={"id": 1})


def event(labels=("bug",), state="open"):
    return {
        "action": "opened",
        "issue": {
            "number": 7,
            "title": "Export crashes on save",
            "body": "**Expected result:** It saves\n**Actual result:** It crashes",
            "state": state,
            "labels": [{"name": n} for n in labels],
            "type": None,
        },
    }


def client(server):
    return httpx.Client(
        base_url="https://api.github.com", transport=httpx.MockTransport(server)
    )


def run_with(server, ev, loads):
    def load_agent():
        loads.append(1)
        return FakeAgent()

    return run(ev, "octo/app", client(server), load_agent, "v1")


def test_bug_gets_a_comment():
    server, loads = FakeGitHub(), []
    assert run_with(server, event(), loads) == "created"
    assert loads == [1]
    [body] = server.posted
    assert "**Steps to reproduce**" in body
    assert "status **Submitted**" in body


@pytest.mark.parametrize("ev", [event(labels=["enhancement"]), event(state="closed")])
def test_not_a_bug_or_closed_is_not_checked_and_the_model_not_loaded(ev):
    server, loads = FakeGitHub(), []
    assert run_with(server, ev, loads) == "not checked"
    assert (loads, server.posted) == ([], [])


def test_team_config_is_read_from_the_repository():
    server, loads = FakeGitHub("status_labels: [Triaged]\n"), []
    # An open bug without a status label is Submitted, not in the team's list.
    assert run_with(server, event(), loads) == "not checked"
    assert run_with(server, event(labels=["bug", "Triaged"]), loads) == "created"


def test_event_without_an_issue_only_caches_the_model():
    # push / schedule / workflow_dispatch may write the cache; issues events may not.
    server, loads = FakeGitHub(), []
    assert run_with(server, {"ref": "refs/heads/main"}, loads) == "model cached"
    assert (loads, server.posted) == ([1], [])


def test_bad_config_fails_before_the_model():
    server, loads = FakeGitHub("treshold: 0.9"), []
    with pytest.raises(ConfigError, match="treshold"):
        run_with(server, event(), loads)
    assert loads == []
