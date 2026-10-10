from bug_report_checker.comment import is_complete, render
from bug_report_checker.decide import MISSING, PRESENT, UNSURE, Decision
from bug_report_checker.questions import QUESTIONS


def decision(long=False, environments=(), image_only=(), **verdicts):
    return Decision(
        verdicts={c: verdicts.get(c, PRESENT) for c in QUESTIONS},
        long=long,
        environments=list(environments),
        image_only=list(image_only),
        strict=False,
    )


def test_full_bug():
    d = decision()
    assert is_complete(d)
    assert render(d, "Open") == (
        "✅ **Bug report complete.**\n"
        "\n"
        "<sub>Checked in status **Open** by bug-report-checker.</sub>"
    )


def test_bug_with_blockers():
    d = decision(steps=MISSING, build_version=MISSING, expected=UNSURE)
    assert not is_complete(d)
    assert render(d, "Submitted") == (
        "**Some details are missing from this bug report.**\n"
        "\n"
        "Missing:\n"
        "- **Steps to reproduce**: list the steps that lead to the problem."
        " If they are unknown, describe the conditions in which it happened.\n"
        "- **Build version**: name the exact build where you saw the bug,"
        " not latest or the current prod.\n"
        "\n"
        "Not sure about: **Expected result**. Please check it yourself.\n"
        "\n"
        "<sub>Checked in status **Submitted** by bug-report-checker.</sub>"
    )


def test_bug_with_only_suggestions():
    d = decision(summary_where=MISSING, summary_when=MISSING, image_only=["actual"])
    assert is_complete(d)
    assert render(d, "Open") == (
        "✅ **Bug report complete.**\n"
        "\n"
        "<details>\n"
        "<summary>Suggestions (3)</summary>\n"
        "\n"
        "- Name in the title where it happens: a screen, feature or component.\n"
        "- Name in the title when it happens: the action or condition.\n"
        "- Describe the actual result in text too, not only as a screenshot.\n"
        "\n"
        "</details>\n"
        "\n"
        "<sub>Checked in status **Open** by bug-report-checker.</sub>"
    )


def test_only_unsure_blockers_is_not_complete():
    d = decision(actual=UNSURE, steps=UNSURE)
    assert not is_complete(d)
    assert render(d, "Open").startswith(
        "**Could not check everything in this bug report.**\n"
        "\n"
        "Not sure about: **Steps to reproduce**, **Actual result**."
        " Please check them yourself.\n"
    )


def test_unsure_hint_is_not_shown():
    # A hint the model is unsure of is simply not given.
    assert "Suggestions" not in render(decision(summary_what=UNSURE), "Open")


def test_long_report_and_environment_are_noted():
    d = decision(long=True, environments=["staging", "prod"], expected=UNSURE)
    assert render(d, "In Progress").endswith(
        "This report is long and was read in parts, so details found in it"
        " could not be confirmed.\n"
        "\n"
        "<sub>Checked in status **In Progress** by bug-report-checker."
        " Environment: staging, prod.</sub>"
    )


def test_strict_mode_says_what_counts():
    d = Decision(
        verdicts={c: MISSING if c == "actual" else PRESENT for c in QUESTIONS},
        long=False,
        environments=[],
        image_only=[],
        strict=True,
    )
    text = render(d, "Submitted")
    assert "error text, the wrong value, a log or a screenshot" in text
    assert "describe what happened instead" not in text
