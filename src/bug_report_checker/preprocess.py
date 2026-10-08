"""Text preprocessing shared by training, eval and the Action.

The model must see the same text in all three places, so every rule lives here once.
"""

import re

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# GFM strikethrough: may wrap lines inside a paragraph, never crosses a blank line.
_STRIKETHROUGH = re.compile(r"~~(?:(?!\n[ \t]*\n).)+?~~", re.DOTALL)
# `Word:` prefixes are left alone: in real data they often carry the defect itself
# ("Crash:", "Regression:", "...Exception:"), not an area tag.
_SUMMARY_TAGS = re.compile(r"^\s*(?:\[[^\]]*\]\s*)+")
_MEDIA_EXT = r"(?:png|jpe?g|gif|bmp|svg|webp|mp4|mov|webm|avi)"
_MEDIA = re.compile(
    "|".join(
        [
            r"!\[[^\]]*\]\([^)\s]*\)(?:\{[^}\n]*\})?",  # markdown, YouTrack {width=}
            r"<img\b[^>]*>",  # HTML, GitHub drag-and-drop
            r"https://github\.com/user-attachments/assets/[\w-]+",  # GitHub video
            # Jira !file.png!, !file.png?x=1|thumbnail!, !https://host/any!
            r"!(?:https?://[^!\s]+"
            rf"|(?=[^!\s])[^!\n]*?\.{_MEDIA_EXT}(?:\?[^!|\n]*)?)(?:\|[^!\n]*)?!",
            r"\[\^[^\]\n]+\]",  # Jira attachment [^file]
        ]
    ),
    re.IGNORECASE,
)
_MD_LINK = re.compile(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)")
_URL = re.compile(r"<?https?://([^/\s<>\"'()]+)(?:[^\s<>\"']*[^\s<>\"'.,;:!?)\]])?>?")
CODE_LINES = 5
TRUNCATED = "[… truncated]"
_FENCE = re.compile(r"^([ \t]*```[^`\n]*\n)(.*?)(\n[ \t]*```[ \t]*)$", re.DOTALL | re.M)
_JIRA_CODE = re.compile(
    r"\{(code|noformat)(?::[^}\n]*)?\}(.*?)\{\1\}", re.DOTALL | re.IGNORECASE
)
# Unfenced traces: JVM / .NET / JS frames, or a Python traceback up to its error line.
_STACK_FRAME = (
    r"[ \t]*(?:at [\w$.<>/@-]+ ?\(.*|Caused by: .*|Suppressed: .*"
    r"|\.\.\. \d+ (?:more|common frames omitted))"
)
_STACKTRACE = re.compile(
    rf"(?:^{_STACK_FRAME}(?:\n|\Z))+"
    r"|^Traceback \(most recent call last\):[ \t]*\n(?:[ \t]+.*(?:\n|\Z))+",
    re.MULTILINE,
)
_CODE_SPAN = re.compile(
    r"(^[ \t]*```[^\n]*\n.*?\n[ \t]*```[ \t]*$|`[^`\n]+`)", re.DOTALL | re.M
)
_JIRA_MONO = re.compile(r"\{\{(.+?)\}\}")
_JIRA_HEADING = re.compile(r"^h([1-6])\.[ \t]+", re.M)
_JIRA_LIST = re.compile(r"^[ \t]*([*#]+|-)[ \t]+(?=\S)", re.M)
_JIRA_BOLD = re.compile(r"(?<![\w*])\*(?=[^\s*])([^*\n]*?[^\s*])\*(?![\w*])")
# Opens only after a space or an opening bracket/quote: logs are full of `=-`, `->`.
_JIRA_STRIKE = re.compile(r"(?<![^\s(\[\"'*])-(?=[^\s>-])([^-\n]*?[^\s-])-(?![\w>-])")
_JIRA_LINK = re.compile(
    r"\[([^\]|\n]+)\|((?:https?|mailto):[^\]|\s]+)(?:\|[^\]\n]*)?\]"
)
_JIRA_BARE_LINK = re.compile(r"\[((?:https?|mailto):[^\]|\s]+)\]")
_JIRA_WRAPPER = re.compile(r"\{(?:color|panel|quote)(?::[^}\n]*)?\}")
_JIRA_RULE = re.compile(r"^-{4,}[ \t]*$", re.M)
_BLANK_LINES = re.compile(r"\n{3,}")


def strip_html_comments(text: str) -> str:
    """Drop `<!-- ... -->`: template hints often stay in the text after it is filled."""
    return _HTML_COMMENT.sub("", text)


def strip_strikethrough(text: str) -> str:
    """Drop `~~struck~~` text: it is an outdated value, not part of the report."""
    return _STRIKETHROUGH.sub("", text)


def strip_summary_tags(summary: str) -> str:
    """Drop leading `[Area]` tags: they are optional and never count as WHERE."""
    return _SUMMARY_TAGS.sub("", summary).strip()


def replace_media(text: str) -> str:
    """Images, videos, attachments -> `[image]`: the model sees an attachment."""
    return _MEDIA.sub("[image]", text)


def replace_links(text: str) -> str:
    """Links -> `[link: host]`; the host keeps the environment signal (stand, prod)."""
    text = _MD_LINK.sub(_md_link, text)
    return _URL.sub(r"[link: \1]", text)


def _md_link(m: re.Match) -> str:
    """`[text](url)` -> `text url`: keep the label and the host; a URL label once."""
    label, url = m.groups()
    return url if label.startswith(("http://", "https://")) else f"{label} {url}"


def _head(code: str) -> str:
    lines = code.split("\n")
    if len(lines) <= CODE_LINES:
        return code
    return "\n".join([*lines[:CODE_LINES], TRUNCATED])


def _jira_block(m: re.Match) -> str:
    code = m.group(2).strip("\n")
    if "\n" not in code:
        return f"`{code}`"
    return f"```\n{_head(code)}\n```"


def _trace(m: re.Match) -> str:
    trace = m.group(0)
    end = "\n" if trace.endswith("\n") else ""
    return _head(trace.removesuffix("\n")) + end


def truncate_code(text: str) -> str:
    """Code blocks and stack traces -> first lines + `[… truncated]`.

    The model only needs to see that code or a trace is attached. Jira `{code}` and
    `{noformat}` become markdown fences, as in YouTrack and GitHub.
    """
    text = _FENCE.sub(lambda m: m.group(1) + _head(m.group(2)) + m.group(3), text)
    text = _JIRA_CODE.sub(_jira_block, text)
    return _STACKTRACE.sub(_trace, text)


def _list_item(m: re.Match) -> str:
    markers = m.group(1)
    bullet = "1." if markers[-1] == "#" else "*"
    return "  " * (len(markers) - 1) + bullet + " "


def _jira_prose(text: str) -> str:
    text = _JIRA_RULE.sub("---", text)
    text = _JIRA_LIST.sub(_list_item, text)  # before headings: they start with `#`
    text = _JIRA_HEADING.sub(lambda m: "#" * int(m.group(1)) + " ", text)
    text = _JIRA_BOLD.sub(r"**\1**", text)
    text = _JIRA_STRIKE.sub(r"~~\1~~", text)
    text = _JIRA_LINK.sub(r"[\1](\2)", text)
    text = _JIRA_BARE_LINK.sub(r"\1", text)
    return _JIRA_WRAPPER.sub("", text)


def jira_to_markdown(text: str) -> str:
    """Jira wiki -> markdown, so the model does not learn the format difference.

    Only for Jira text: `# x` is a list in Jira but a heading in markdown. Expects
    `truncate_code` to have run, so code is already in fences; code is left as is.
    """
    text = _JIRA_MONO.sub(r"`\1`", text)
    parts = _CODE_SPAN.split(text)
    parts[::2] = map(_jira_prose, parts[::2])
    return "".join(parts)


def preprocess(
    summary: str, description: str | None, *, jira: bool = False
) -> dict[str, str]:
    """Model state for one bug report; `jira=True` only for Jira wiki text.

    Order matters: code is cut first so later rules do not parse it, Jira markup
    becomes markdown before links are replaced (`[text|url]`), media before links.
    """
    text = (description or "").replace("\r\n", "\n").replace("\r", "\n")
    text = strip_html_comments(text)
    text = truncate_code(text)
    if jira:
        text = jira_to_markdown(text)
    text = strip_strikethrough(text)
    text = replace_media(text)
    text = replace_links(text)
    text = _BLANK_LINES.sub("\n\n", text)
    return {"summary": strip_summary_tags(summary), "description": text.strip()}
