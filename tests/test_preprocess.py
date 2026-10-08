import pytest

from bug_report_checker.preprocess import (
    jira_to_markdown,
    preprocess,
    replace_links,
    replace_media,
    strip_html_comments,
    strip_strikethrough,
    strip_summary_tags,
    truncate_code,
    unescape_entities,
)

LINES = "\n".join(f"line {i}" for i in range(1, 9))
HEAD = "\n".join(f"line {i}" for i in range(1, 6)) + "\n[… truncated]"
FRAMES = "\n".join(f"\tat com.example.Foo.bar{i}(Foo.java:{i})" for i in range(8))


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
        (
            "[build log](https://ci.example.com/job/1)",
            "build log [link: ci.example.com]",
        ),
        (
            "[https://ci.example.com/1](https://ci.example.com/1)",
            "[link: ci.example.com]",
        ),
        ("Build version: 2026.09-dev-118", "Build version: 2026.09-dev-118"),
    ],
)
def test_replace_links(text, expected):
    assert replace_links(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (f"Log:\n```\n{LINES}\n```\nAfter", f"Log:\n```\n{HEAD}\n```\nAfter"),
        ("```python\nx = 1\ny = 2\n```", "```python\nx = 1\ny = 2\n```"),
        (f"{{code:java}}\n{LINES}\n{{code}}", f"```\n{HEAD}\n```"),
        ("{noformat}\nERROR 1\nERROR 2\n{noformat}", "```\nERROR 1\nERROR 2\n```"),
        ("Call {code}save(){code} twice", "Call `save()` twice"),
        ("```\nunclosed\nfence", "```\nunclosed\nfence"),
    ],
    ids=["fence-long", "fence-short", "jira-code", "jira-noformat", "inline", "open"],
)
def test_truncate_code_blocks(text, expected):
    assert truncate_code(text) == expected


def test_truncate_code_bare_java_stacktrace_keeps_message():
    text = f"java.lang.IllegalStateException: boom\n{FRAMES}\nSteps: open"
    head = "\n".join(FRAMES.split("\n")[:5])
    expected = (
        f"java.lang.IllegalStateException: boom\n{head}\n[… truncated]\nSteps: open"
    )
    assert truncate_code(text) == expected


def test_truncate_code_counts_caused_by_and_more_as_trace():
    text = (
        "\tat a.B.c(B.java:1)\n\tat a.B.d(B.java:2)\n"
        "Caused by: java.io.IOException: closed\n"
        "\tat a.C.e(C.java:3)\n\tat a.C.f(C.java:4)\n\t... 12 more"
    )
    expected = "\n".join(text.split("\n")[:5]) + "\n[… truncated]"
    assert truncate_code(text) == expected


def test_truncate_code_bare_python_traceback_keeps_error_line():
    frames = "".join(
        f'  File "app.py", line {i}, in f{i}\n    f{i}()\n' for i in range(4)
    )
    text = f"Traceback (most recent call last):\n{frames}ValueError: bad"
    head = "\n".join(text.split("\n")[:5])
    assert truncate_code(text) == f"{head}\n[… truncated]\nValueError: bad"


@pytest.mark.parametrize(
    "text",
    [
        "We met at home (twice) and at work (once).",
        "\tat a.B.c(B.java:1)\n\tat a.B.d(B.java:2)",
        "Plain text\nwith lines",
    ],
)
def test_truncate_code_leaves_short_or_plain_text(text):
    assert truncate_code(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("doesn&#x27;t work", "doesn't work"),
        ("&lt;div&gt; &amp; &quot;x&quot; &#39;y&#39;", "<div> & \"x\" 'y'"),
        ("?a=1&copy=2&lt", "?a=1&copy=2&lt"),
        ("AT&T and R&D", "AT&T and R&D"),
    ],
)
def test_unescape_entities_only_with_semicolon(text, expected):
    assert unescape_entities(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("h3. Steps to reproduce", "### Steps to reproduce"),
        ("h1. Title\nh6. Note", "# Title\n###### Note"),
        ("Click *Save* and *OK*", "Click **Save** and **OK**"),
        ("2 * 3 * 4", "2 * 3 * 4"),
        ("* a\n** b\n# c\n## d\n#* e\n- f", "* a\n  * b\n1. c\n  1. d\n  * e\n* f"),
        ("-old value- new value", "~~old value~~ new value"),
        ("-Xmx512m -Xms256m on 2026-01-02", "-Xmx512m -Xms256m on 2026-01-02"),
        ("a - b - c, well-known", "a - b - c, well-known"),
        ("fill=-,flush=-,to=1", "fill=-,flush=-,to=1"),
        ("(a)->field)->type", "(a)->field)->type"),
        (r"start \-\-log=1 \-\-size=2", r"start \-\-log=1 \-\-size=2"),
        (
            "[build log|https://ci.example.com/1]",
            "[build log](https://ci.example.com/1)",
        ),
        ("[https://example.com/x]", "https://example.com/x"),
        ("[Docs|#anchor] and [~a1b2c3]", "[Docs|#anchor] and [~a1b2c3]"),
        ("Edit {{config.yml}}", "Edit `config.yml`"),
        ("{color:red}Error{color} {quote}cited{quote}", "Error cited"),
        ("{panel:title=Note}\ntext\n{panel}", "\ntext\n"),
        ("above\n----\nbelow", "above\n---\nbelow"),
        ("Hi\\\\\nthere\\\\", "Hi\nthere"),
        (r"open \\server\share now", r"open \\server\share now"),
    ],
)
def test_jira_to_markdown(text, expected):
    assert jira_to_markdown(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "```\nint *ptr* = -1-;\n# not a list\n```",
        "Set `*ptr*` and `-x-`",
    ],
)
def test_jira_to_markdown_leaves_code_alone(text):
    assert jira_to_markdown(text) == text


def test_jira_to_markdown_keeps_monospace_content_literal():
    assert jira_to_markdown("Run {{-Dfoo=*bar*}}") == "Run `-Dfoo=*bar*`"


def test_jira_template_matches_markdown_template():
    jira = (
        "h3. Steps to reproduce\n# Open *Settings*\n# Click {{Save}}\n"
        "h3. Expected result\nSaved. -Was: closed-\n"
        "h3. Actual result\nError, see [log|https://ci.example.com/1]"
    )
    markdown = (
        "### Steps to reproduce\n1. Open **Settings**\n1. Click `Save`\n"
        "### Expected result\nSaved. ~~Was: closed~~\n"
        "### Actual result\nError, see [log](https://ci.example.com/1)"
    )
    assert jira_to_markdown(jira) == markdown


def test_preprocess_jira_bug_applies_all_rules():
    description = (
        "h3. Steps to reproduce\r\n"
        "# Open {{Settings}} on [stand|https://dev1.example.com/app?x=1]\r\n"
        "# Click *Save*\r\n"
        "\r\n\r\n\r\n"
        "h3. Expected result\r\n"
        "Saved. -Was: dialog closes-\r\n"
        "h3. Actual result\r\n"
        "!error.png|thumbnail!\r\n"
        "{code:java}\r\n"
        + "\r\n".join(f"\tat a.B.m{i}(B.java:{i})" for i in range(8))
        + "\r\n{code}\r\n"
        "Logs: https://ci.example.com/job/7 <!-- attach logs -->"
    )
    state = preprocess("[Billing][API] Export fails", description, jira=True)
    frames = "\n".join(f"\tat a.B.m{i}(B.java:{i})" for i in range(5))
    assert state == {
        "summary": "Export fails",
        "description": (
            "### Steps to reproduce\n"
            "1. Open `Settings` on stand [link: dev1.example.com]\n"
            "1. Click **Save**\n"
            "\n"
            "### Expected result\n"
            "Saved. \n"
            "### Actual result\n"
            "[image]\n"
            f"```\n{frames}\n[… truncated]\n```\n"
            "Logs: [link: ci.example.com]"
        ),
    }


def test_preprocess_markdown_bug_keeps_markdown_syntax():
    description = "# Steps\n1. Open *Settings*\n\n![](shot.png)"
    assert preprocess("Export fails", description) == {
        "summary": "Export fails",
        "description": "# Steps\n1. Open *Settings*\n\n[image]",
    }


def test_preprocess_empty_description():
    assert preprocess(" Export fails ", None) == {
        "summary": "Export fails",
        "description": "",
    }
