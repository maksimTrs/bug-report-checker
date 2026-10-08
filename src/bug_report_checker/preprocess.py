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
_MD_LINK = re.compile(r"\[([^\]\n]+)\]\(https?://[^)\s]+\)")
_URL = re.compile(r"<?https?://([^/\s<>\"'()]+)(?:[^\s<>\"']*[^\s<>\"'.,;:!?)\]])?>?")


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
    text = _MD_LINK.sub(r"\1", text)
    return _URL.sub(r"[link: \1]", text)
