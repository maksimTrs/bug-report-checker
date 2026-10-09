from bug_report_checker.github import from_github
from bug_report_checker.issue import BUG, OTHER, Issue


def gh(labels=(), state="open", body="Steps", type_name=None, title="Crash on save"):
    """A GitHub issue object as webhook events carry it, trimmed to what we read."""
    return {
        "title": title,
        "body": body,
        "state": state,
        "labels": [{"name": n} for n in labels],
        "type": {"name": type_name} if type_name else None,
    }


def test_bug_label_gives_bug_type_and_keeps_text():
    issue = from_github(gh(labels=["bug", "Open"]))
    assert issue == Issue(BUG, "Open", "Crash on save", "Steps")


def test_labels_match_case_insensitively_and_keep_the_configured_name():
    issue = from_github(gh(labels=["BUG", "in progress"]))
    assert (issue.type, issue.state) == (BUG, "In Progress")


def test_native_issue_type_bug_counts_without_label():
    assert from_github(gh(type_name="Bug")).type == BUG


def test_other_issue_is_not_a_bug():
    assert from_github(gh(labels=["enhancement"], type_name="Feature")).type == OTHER


def test_open_issue_without_status_label_is_submitted():
    # A new GitHub issue has no status yet: in YouTrack it would be Submitted.
    assert from_github(gh(labels=["bug"])).state == "Submitted"


def test_unknown_status_label_is_not_recognised():
    # Labels outside the configured list are not statuses (decision 2026-10-09).
    assert from_github(gh(labels=["bug", "In Clarification"])).state == "Submitted"


def test_closed_issue_has_no_state():
    assert from_github(gh(labels=["bug", "Open"], state="closed")).state is None


def test_first_configured_status_wins_when_several_labels():
    assert from_github(gh(labels=["In Progress", "Open"])).state == "Open"


def test_custom_labels():
    issue = from_github(
        gh(labels=["defect", "triage"]),
        bug_labels=("defect",),
        status_labels=("Triage",),
    )
    assert (issue.type, issue.state) == (BUG, "Triage")


def test_missing_body_is_empty_description():
    assert from_github(gh(body=None)).description == ""


def test_issue_form_empty_answers_are_dropped_and_headings_kept():
    body = (
        "### Build version\n\n_No response_\n\n"
        "### Steps to reproduce\n\n1. Open a report\n\n"
        "### Expected result\n\n_No response_"
    )
    assert from_github(gh(body=body)).description == (
        "### Build version\n\n\n\n"
        "### Steps to reproduce\n\n1. Open a report\n\n"
        "### Expected result\n\n"
    )


def test_no_response_inside_text_is_kept():
    body = "The dialog says _No response_ and closes"
    assert from_github(gh(body=body)).description == body
