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


# `### Actual result`, `**Expected result:**`, `**Actual**:`, `Steps to reproduce:`.
_SECTION_HEAD = re.compile(
    r"^[ \t]*(#{1,6}[ \t]*)?(\*\*)?[ \t]*(actual|expected|steps)"
    r"(?:[ \t]+(?:results?|behaviou?r|to[ \t]+reproduce))?"
    r"[ \t]*(:)?[ \t]*(\*\*)?[ \t]*(:)?(.*)$",
    re.IGNORECASE,
)
# Any field heading ends a section: markdown (not a `# code` list item), bold, or a
# short `Label:` alone on its line; `UPD: the fix…` or a sentence ending in a colon
# is text.
_ANY_HEAD = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]+[^`\s]|\*\*[^*\n]+\*\*"
    r"|[A-Z][\w()/'-]*(?:[ \t]+[\w()/'-]+){0,3}[ \t]*:[ \t]*$)"
)
_ONLY_MEDIA = re.compile(r"(?:\s|[-*]|\d+\.|\[image\])*")
# Left as the template had it: blank, `1.` `2.`, `-`, TBD, N/A.
_BLANK = re.compile(r"(?:\s|[-*.]|\d+\.|tbd|n/?a)*", re.IGNORECASE)


def _sections(description: str) -> list[tuple[str, str]]:
    """(field, content) for each Steps / Actual / Expected heading."""
    lines = description.split("\n")
    heads = [_section_head(line) for line in lines]
    found = []
    for i, m in enumerate(heads):
        if not m:
            continue
        body = [m[7]]
        for nxt, nxt_head in zip(lines[i + 1 :], heads[i + 1 :], strict=True):
            if nxt_head or _ANY_HEAD.match(nxt):
                break
            body.append(nxt)
        found.append((m[3].lower(), "\n".join(body)))
    return found


def _section_head(line: str) -> re.Match | None:
    """A heading needs a heading form: `#`, bold or a colon, not just the word."""
    m = _SECTION_HEAD.match(line)
    return m if m and (m[1] or (m[2] and m[5]) or m[4] or m[6]) else None


def image_only(state: dict[str, str]) -> list[str]:
    """Actual / Expected sections holding only `[image]`: a hint to describe the
    result in text too. Needs headings, so free-form reports never get it."""
    found = {
        field
        for field, content in _sections(state["description"])
        if field != "steps" and "[image]" in content and _ONLY_MEDIA.fullmatch(content)
    }
    return [f for f in ("actual", "expected") if f in found]


def empty_sections(state: dict[str, str]) -> list[str]:
    """Steps / Expected headings left empty: "missing" by the rubric, whatever the
    model reads into the heading. Actual is left out: the summary may state it."""
    sections = _sections(state["description"])
    filled = {f for f, content in sections if not _BLANK.fullmatch(content)}
    empty = {f for f, content in sections if _BLANK.fullmatch(content)}
    return [f for f in ("steps", "expected") if f in empty - filled]
