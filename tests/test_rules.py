import pytest

from bug_report_checker.preprocess import preprocess
from bug_report_checker.rules import (
    build_version,
    empty_sections,
    environment,
    image_only,
    strict_missing,
)

# An invented build format: a team's real one lives only in its own config.
PATTERN = r"\bR\d{2}\.\d{2}-(?:\d+|dev|hf-\w+)\b"


def state(description, summary="Export crashes on save"):
    return preprocess(summary, description)


@pytest.mark.parametrize(
    "description",
    [
        "**Build version:** R26.03-412",
        "**Build version:** R26.03-dev",
        "**Build version:**\nR26.03-hf-cart",
        "### Build version\n\nBuild #R26.03-412",
        "Seen on R26.03-412 after the update.",
    ],
)
def test_team_format_anywhere_is_present(description):
    assert build_version(state(description), PATTERN) is True


def test_team_format_in_summary_counts():
    assert build_version(state("Steps", "Crash in R26.03-412"), PATTERN) is True


@pytest.mark.parametrize(
    "description",
    [
        "**Build version:** current prod",
        "**Build version:** Current master",
        "**Build version:**\nlatest",
        "### Build version\n\nLatest build",
        "Build: prod",
        "**Version:** master",
        "**Build version:**\nprod as of today",
    ],
)
def test_vague_build_field_is_missing_even_without_pattern(description):
    assert build_version(state(description), PATTERN) is False
    assert build_version(state(description), None) is False


@pytest.mark.parametrize(
    "description",
    [
        "**Build version:** Windows 11, Chrome 120",  # OS / browser: model decides
        "**Build version:**\n**Steps to reproduce:**\n1. Open",  # empty field
        "### Build version\n\n",  # issue form, skipped field
        "The latest change broke export.",  # "latest" outside the build field
        "Version 4.18.2 of the app",  # another format: the model knows versions
        "**Build version:** prod 4.18.2",  # a number after prod may be the build
        "**Build version:** master a1b2c3d",  # a commit is a build
        "",
    ],
)
def test_otherwise_the_model_decides(description):
    assert build_version(state(description), PATTERN) is None


def test_without_pattern_a_number_goes_to_the_model():
    assert build_version(state("**Build version:** R26.03-412"), None) is None


def test_template_hint_in_html_comment_is_not_a_build():
    hint = "**Build version:** <!-- e.g. R26.03-412 -->\n**Steps to reproduce:**"
    assert build_version(state(hint), PATTERN) is None


def test_pattern_wins_over_a_vague_word():
    assert build_version(state("**Build version:** latest, R26.03-412"), PATTERN)


STANDS = ("staging", "qa1")


@pytest.mark.parametrize(
    ("description", "found"),
    [
        ("Reproduced on QA1 after login.", ["qa1"]),
        ("Open https://qa1.example.com/cart and pay", ["qa1"]),  # host of a link
        ("**Build version:** R26.03-412 (staging)", ["staging"]),
        ("Seen on staging and on prod", ["staging", "prod"]),
        ("Only in production", ["prod"]),
        ("**Build version:** current prod", ["prod"]),
    ],
)
def test_environment_names_stands_and_prod(description, found):
    assert environment(state(description), STANDS) == found


@pytest.mark.parametrize(
    "description",
    [
        "**Build version:** Windows 11, Chrome 120",  # OS / browser is not a stand
        "The product page crashes",  # "prod" inside a word
        "Fails on qa10",  # another stand
        "",
    ],
)
def test_no_environment(description):
    assert environment(state(description), STANDS) == []


def test_environment_in_summary_counts():
    assert environment(state("Steps", "Checkout fails on staging"), STANDS) == [
        "staging"
    ]


@pytest.mark.parametrize(
    ("description", "fields"),
    [
        (
            "**Actual result:**\n![shot](a.png)\n**Expected result:** It saves",
            ["actual"],
        ),
        (
            "**Actual result:** saves twice\n**Expected result:** <img src=x>",
            ["expected"],
        ),
        (
            "### Actual result\n\n![a](a.png) ![b](b.png)\n\n### Expected result\n\n"
            "![c](c.png)",
            ["actual", "expected"],
        ),
        ("Actual result:\n- ![a](a.png)\nExpected result: Saved\n", ["actual"]),
    ],
)
def test_image_only_sections(description, fields):
    assert image_only(state(description)) == fields


@pytest.mark.parametrize(
    "description",
    [
        "**Actual result:** ![a](a.png) the dialog closes\n**Expected result:** Saved",
        "**Actual result:**\n**Expected result:** Saved",  # empty: the model says no
        "Export crashes, see ![a](a.png)",  # free form: no headings, no hint
        "![a](a.png)",
    ],
)
def test_no_image_only_hint(description):
    assert image_only(state(description)) == []


@pytest.mark.parametrize(
    ("description", "fields"),
    [
        (
            "### Build version\n\n### Steps to reproduce\n\n### Actual result\n\n"
            "Blank page\n\n### Expected result\n\nA5 pages",
            ["steps"],
        ),
        (
            "**Steps to reproduce:**\n1.\n2.\n**Expected result:** TBD",
            ["steps", "expected"],
        ),
        ("**Steps to reproduce:**\n1. Open\n**Expected result:**\n-\n", ["expected"]),
        ("Steps:\n\nExpected result:\nN/A", ["steps", "expected"]),
    ],
)
def test_empty_steps_and_expected_sections(description, fields):
    assert empty_sections(state(description)) == fields


@pytest.mark.parametrize(
    "description",
    [
        "**Actual result:**\n**Expected result:** Saved",  # the summary may say actual
        "**Expected result:** ![a](a.png)",  # a screenshot is not empty
        "Steps are unknown, it just crashes",  # free form: the model decides
        "**Steps to reproduce:**\n**Steps to reproduce:**\n1. Open",  # filled once
        # Lines that look like headings but are text (found in train / eval):
        "**Expected result:**\n UPD: import fails with a clear error",
        "### Expected Results\nThere are two possible results:\n1. Block it",
        "Steps to reproduce:\n\n# `java Server -p 1234`\n# `ssh -p 1234 localhost`",
        "### Steps to Reproduce\n\nMongoDB Enterprise shard-0:PRIMARY> db.version()",
        "",
    ],
)
def test_no_empty_sections(description):
    assert empty_sections(state(description)) == []


# Strict mode (D26, D27): the description alone must state each part.
SANDBOX_8 = "When I try to export pdf, I can see red errors on UI page"


@pytest.mark.parametrize(
    "description",
    [
        "1. Open Shipments\n2. Click Export",
        "**Steps to reproduce:**\nOpen Shipments and click Export.",
        "```\n$ parcelwise export --format pdf\n```",
        "SELECT DATE_ADD('2018-02-01', INTERVAL -188 DAY)",
        "$ python setup.py develop",
        'Assert.assertEquals(false, StringUtils.equals("in", "notin"));',
        "Settings -> Notifications -> SMS alerts",
    ],
)
def test_strict_steps_present(description):
    assert "steps" not in strict_missing(state(description))


@pytest.mark.parametrize(
    "description",
    [
        SANDBOX_8,
        "Clicking Export on the Shipments page downloads an empty CSV file (0 bytes).",
        "",
    ],
)
def test_strict_steps_missing(description):
    assert "steps" in strict_missing(state(description))


@pytest.mark.parametrize(
    "description",
    [
        "Actual: the map is blank.\n\nExpected: the map loads.",
        "The export should keep the column order.",
        "The refund shows 0.00 instead of 24.90.",
        "There needs to be a lock on the Create button.",
        "```\njava.lang.AssertionError: expected:<1> but was:<2>\n```",
        "Expected result: it should not fail.",
        "### Fix Proposal\nCall toString() on every property value.",
    ],
)
def test_strict_expected_present(description):
    assert "expected" not in strict_missing(state(description))


@pytest.mark.parametrize(
    "description",
    [
        SANDBOX_8,
        "After a reload the SMS toggle is on again.",
        "The list shows parcels from 2019 first. Shouldn't the newest be on top?",
        "### Build version\n\nlatest\n\n### Expected result\n\n",
        "```\nerror: expected ';' before '}'\n```",
    ],
)
def test_strict_expected_missing(description):
    assert "expected" in strict_missing(state(description))


@pytest.mark.parametrize(
    "description",
    [
        "Steps:\n1. Open a shipment\n\n[image]",
        'Printing fails with "Printer queue unavailable".',
        '```\nTraceback (most recent call last):\n  File "x.py", line 1\n```',
        "Saving throws a NullPointerException.",
        "The rate endpoint returns null for EU parcels.",
        "Export downloads an empty CSV file (0 bytes).",
        "The Host header is always missing the port.",
    ],
)
def test_strict_actual_present(description):
    assert "actual" not in strict_missing(state(description))


@pytest.mark.parametrize(
    "description",
    [
        SANDBOX_8,
        "It doesn't work.",
        pytest.param(
            "1. Open a shipment\n2. Click Print label\n\nExpected: the label prints.",
            marks=pytest.mark.xfail(
                strict=True,
                reason="known limit (T5.7): list lines outside a Steps heading read"
                " as result text; the symptom is only in the summary",
            ),
        ),
        "Steps:\n1. Log in\n2. Open Route planner\n\nActual: the page is broken.",
        "",
    ],
)
def test_strict_actual_missing(description):
    assert "actual" in strict_missing(state(description))


def test_strict_empty_issue_form_misses_all_three():
    # Sandbox #7 "Doesn't work" after the adapter drops `_No response_`.
    form = (
        "### Build version\n\nlatest\n\n### Steps to reproduce\n\n\n\n"
        "### Actual result\n\n\n\n### Expected result\n\n"
    )
    missing = strict_missing(state(form, "Doesn't work"))
    assert missing == ["steps", "expected", "actual"]


def test_strict_reads_the_description_not_the_summary():
    d = state("", summary="Export fails with 'Printer queue unavailable', should print")
    assert strict_missing(d) == ["steps", "expected", "actual"]
