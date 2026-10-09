"""Checks decided by code before the model: exact where a regex can be exact.

Each takes the preprocessed state, so template hints in HTML comments are gone.
"""

import re

# A build field: `**Build version:** x`, `Build: x`, `### Build version` (issue form).
_BUILD_FIELD = re.compile(
    r"^[ \t]*(?:#+[ \t]*)?(?:\*\*)?[ \t]*(?:build(?:[ \t]+version)?|version)"
    r"[ \t]*:?[ \t]*(?:\*\*)?[ \t]*:?[ \t]*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)
_HEADING = re.compile(r"^[ \t]*(?:#|\*\*)")
# Names a branch or an environment, not the build where the bug was seen.
_VAGUE = re.compile(
    r"^(?:current|latest)\b|^(?:prod|production|master|main)\W*$", re.IGNORECASE
)


def _field_values(description: str) -> list[str]:
    """Value of each build field: on the heading line, or the next non-empty line."""
    values = []
    for m in _BUILD_FIELD.finditer(description):
        value = m.group(1).strip()
        if not value:
            rest = description[m.end() :].lstrip("\n").split("\n", 1)[0]
            value = "" if _HEADING.match(rest) else rest.strip()
        values.append(value)
    return values


def build_version(state: dict[str, str], pattern: str | None) -> bool | None:
    """True / False when code is sure, None when the model decides.

    The team's build format anywhere, the summary too, is a build. A build field
    naming a branch or "latest" is not one, whatever the model would say. Other
    formats and OS / browser in place of a build are left to the model.
    """
    text = f"{state['summary']}\n{state['description']}"
    if pattern and re.search(pattern, text):
        return True
    if any(_VAGUE.search(v) for v in _field_values(state["description"])):
        return False
    return None
