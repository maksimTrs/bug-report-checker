"""Text preprocessing shared by training, eval and the Action.

The model must see the same text in all three places, so every rule lives here once.
"""

import re

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# GFM strikethrough: may wrap lines inside a paragraph, never crosses a blank line.
_STRIKETHROUGH = re.compile(r"~~(?:(?!\n[ \t]*\n).)+?~~", re.DOTALL)


def strip_html_comments(text: str) -> str:
    """Drop `<!-- ... -->`: template hints often stay in the text after it is filled."""
    return _HTML_COMMENT.sub("", text)


def strip_strikethrough(text: str) -> str:
    """Drop `~~struck~~` text: it is an outdated value, not part of the report."""
    return _STRIKETHROUGH.sub("", text)
