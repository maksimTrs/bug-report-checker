import pytest

from bug_report_checker.preprocess import strip_html_comments, strip_strikethrough


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
