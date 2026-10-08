import pytest

from bug_report_checker.preprocess import (
    replace_links,
    replace_media,
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


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Actual: ![screenshot](https://cdn.example.com/a.png)", "Actual: [image]"),
        ("![](a.png){width=70%}", "[image]"),
        ('<img width="600" alt="shot" src="https://cdn.example.com/a.png">', "[image]"),
        ("https://github.com/user-attachments/assets/0f1e-22ab", "[image]"),
        ("!screenshot.png!", "[image]"),
        ("!screenshot.PNG|thumbnail!", "[image]"),
        ("!https://cdn.example.com/x.jpg!", "[image]"),
        ("!https://cdn.example.com/media/x9?format=png&name=small!", "[image]"),
        ("!shot_thumb_51.png?fromIssue=36|thumbnail!", "[image]"),
        ("if (a != null && b != null) {", "if (a != null && b != null) {"),
        ("See [^crash-recording.mp4]", "See [image]"),
        ("It fails!! Really!", "It fails!! Really!"),
        ("This is !important! to fix", "This is !important! to fix"),
    ],
)
def test_replace_media(text, expected):
    assert replace_media(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Logs: https://ci.example.com/job/123/console?full=1 here",
            "Logs: [link: ci.example.com] here",
        ),
        ("Open https://example.com/a/b.", "Open [link: example.com]."),
        ("(see http://localhost:8080/admin)", "(see [link: localhost:8080])"),
        ("<https://dev1.example.com/app>", "[link: dev1.example.com]"),
        ("[build log](https://ci.example.com/job/1)", "build log"),
        ("Build version: 2026.09-dev-118", "Build version: 2026.09-dev-118"),
    ],
)
def test_replace_links(text, expected):
    assert replace_links(text) == expected
