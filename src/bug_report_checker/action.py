"""Entry point of the GitHub Action: one `issues` event -> one comment or nothing.

Network: the GitHub API of the checked repository and the model download from
Hugging Face (cached by the workflow); nothing else.
"""

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path

import httpx

from bug_report_checker.comment import is_complete, render
from bug_report_checker.config import FILE, Config, ConfigError, parse_config
from bug_report_checker.core import should_check
from bug_report_checker.decide import decide
from bug_report_checker.github import from_github
from bug_report_checker.preprocess import preprocess
from bug_report_checker.publish import Comments, fingerprint, run_check

API = "https://api.github.com"
API_VERSION = "2022-11-28"


def read_config(client: httpx.Client, repo: str) -> Config:
    """The config on the default branch; defaults when the repository has none."""
    r = client.get(
        f"/repos/{repo}/contents/{FILE}",
        headers={"Accept": "application/vnd.github.raw+json"},
    )
    if r.status_code == 404:
        return Config()
    r.raise_for_status()
    return parse_config(r.text)


def run(
    event: dict, repo: str, client: httpx.Client, load_agent: Callable[[], object]
) -> str:
    """What happened: "not checked" or a `publish` outcome. The model is loaded
    only when a check needs it.

    An event without an issue (push, schedule, workflow_dispatch) only downloads the
    model: `issues` runs get a read-only Actions cache, so a trusted event fills it.
    """
    if "issue" not in event:
        load_agent()
        return "model cached"
    config = read_config(client, repo)
    issue = from_github(
        event["issue"],
        bug_labels=config.bug_labels,
        status_labels=config.status_labels,
    )
    if not should_check(issue, config.status_labels):
        return "not checked"
    state = preprocess(issue.summary, issue.description)

    def make_body() -> tuple[str, bool]:
        d = decide(load_agent(), state, config)
        return render(d, issue.state), is_complete(d)

    return run_check(
        Comments(client, repo, event["issue"]["number"]),
        fingerprint(state, issue.state, config),
        make_body,
        comment_on_success=config.comment_on_success,
    )


def main() -> None:
    import laya

    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text("utf-8"))
    headers = {
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
    }

    def load_agent():
        return laya.load(
            os.environ["MODEL"], device="cpu", revision=os.environ["MODEL_REVISION"]
        )

    with httpx.Client(base_url=API, headers=headers, timeout=30) as client:
        try:
            outcome = run(event, os.environ["GITHUB_REPOSITORY"], client, load_agent)
        except ConfigError as e:
            print(f"::error file={FILE}::{e}")
            sys.exit(1)
    print(f"bug-report-checker: {outcome}")


if __name__ == "__main__":
    main()
