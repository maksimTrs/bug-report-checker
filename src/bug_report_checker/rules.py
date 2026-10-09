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
# Names a branch or an environment, not the build where the bug was seen; with a
# digit ("prod 4.18.2", "master a1b2c3d") it may be a build, so the model decides.
_VAGUE = re.compile(r"^(?:current|latest|prod|production|master|main)\b\D*$", re.I)


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


_PROD = re.compile(r"\bprod(?:uction)?\b", re.IGNORECASE)


def environment(state: dict[str, str], stands: tuple[str, ...]) -> list[str]:
    """Stands from the config, then prod, named anywhere: in text, a link's host,
    the build field. Information only: it never makes a report incomplete."""
    text = f"{state['summary']}\n{state['description']}"
    found = [s for s in stands if re.search(rf"\b{re.escape(s)}\b", text, re.I)]
    return found + ["prod"] if _PROD.search(text) else found


# `### Actual result`, `**Expected result:**`, `**Actual**:`, `Actual results:`.
_RESULT_HEAD = re.compile(
    r"^[ \t]*(#{1,6}[ \t]*)?(\*\*)?[ \t]*(actual|expected)"
    r"(?:[ \t]+(?:results?|behaviou?r))?[ \t]*(:)?[ \t]*(\*\*)?[ \t]*(:)?(.*)$",
    re.IGNORECASE,
)
# Any field heading ends a section: markdown, bold, or `Label:` at a line start.
_ANY_HEAD = re.compile(r"^[ \t]*(?:#{1,6}[ \t]|\*\*[^*\n]+\*\*|[A-Z][\w ()/'-]{0,40}:)")
_ONLY_MEDIA = re.compile(r"(?:\s|[-*]|\d+\.|\[image\])*")


def image_only(state: dict[str, str]) -> list[str]:
    """Actual / Expected sections holding only `[image]`: a hint to describe the
    result in text too. Needs headings, so free-form reports never get it."""
    lines = state["description"].split("\n")
    found = set()
    for i, line in enumerate(lines):
        m = _RESULT_HEAD.match(line)
        if not m or not (m[1] or (m[2] and m[5]) or m[4] or m[6]):
            continue
        body = [m[7]]
        for nxt in lines[i + 1 :]:
            if _ANY_HEAD.match(nxt):
                break
            body.append(nxt)
        content = "\n".join(body)
        if "[image]" in content and _ONLY_MEDIA.fullmatch(content):
            found.add(m[3].lower())
    return [f for f in ("actual", "expected") if f in found]
