import pytest

from bug_report_checker.preprocess import preprocess
from bug_report_checker.rules import build_version, environment, image_only

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
