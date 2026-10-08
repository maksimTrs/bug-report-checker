import pytest

from bug_report_checker.preprocess import (
    strip_html_comments,
    strip_strikethrough,
    strip_summary_tags,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Source: <!-- who asked -->", "Source: "),
        ("a\n<!--\nfill in\nthe source\n-->\nb", "a\n\nb"),
        ("<!-- one --> keep <!-- two -->", " keep "),
        ("No comments here.", "No comments here."),
        ("Unclosed <!-- stays", "Unclosed <!-- stays"),
    ],
)
def test_strip_html_comments(text, expected):
    assert strip_html_comments(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Expected: ~~old value~~ UPD: new value", "Expected:  UPD: new value"),
        ("~~a~~ and ~~b~~", " and "),
        ("Takes ~5 minutes, maybe ~10", "Takes ~5 minutes, maybe ~10"),
        ("~~first paragraph\n\nsecond~~", "~~first paragraph\n\nsecond~~"),
        ("~~line one\nline two~~ rest", " rest"),
    ],
)
def test_strip_strikethrough(text, expected):
    assert strip_strikethrough(text) == expected


@pytest.mark.parametrize(
    ("summary", "expected"),
    [
        ("[Billing] Export to CSV fails", "Export to CSV fails"),
        ("[Billing][API] Export fails", "Export fails"),
        ("  [Billing]  [API]   Export fails", "Export fails"),
        ("[Billing]", ""),
        ("Export [beta] fails on save", "Export [beta] fails on save"),
        ("Crash: app closes on save", "Crash: app closes on save"),
        ("Windows: installer hangs", "Windows: installer hangs"),
        ("Plain summary", "Plain summary"),
    ],
)
def test_strip_summary_tags_removes_only_leading_brackets(summary, expected):
    assert strip_summary_tags(summary) == expected
