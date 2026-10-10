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


# Strict mode (D26, D27): the description itself must state each part. Measured on
# the strict gold `eval/strict_gold.jsonl`; the boundaries are Max's (T5.7).
_CODE_BLOCK = re.compile(r"```.*?(?:```|\Z)", re.S)
_LIST_ITEM = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s+\S", re.M)
# One runnable command, query, call or snippet is a repro, fenced or not.
_COMMAND = re.compile(
    r"^[ \t]*(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|CALL)[ \t]+\S"
    r"|^[ \t]*(?:\$|C:\\[^>\n]*>)[ \t]*\S"
    r"|^[ \t]*[\w$.]+\([^\n]*\)[ \t]*;?[ \t]*$"
    r"|^[^\n]*\{[ \t]*$(?:\n[^\n]*){1,30}?\n[ \t]*\}"
    r"|`[^`\n]*[ (][^`\n]*`",
    re.M,
)
_MENU_PATH = re.compile(r"\S+\s*(?:->|>>|>|→)\s*\S+\s*(?:->|>>|>|→)\s*\S+")

_EXPECT_WORDS = re.compile(
    r"\b(?:should(?:n'?t)?|expected|expect(?:s|ing)?|must|instead\s+of"
    r"|supposed\s+to|ought\s+to|needs?\s+to|suggest\w*|propos\w+)\b",
    re.I,
)
# A test assertion states the expected value: `expected:<1> but was:<2>`.
_ASSERT = re.compile(r"\bexpected:?\s*<|\bexpected:?\s*\S+\s+but\s+(?:was|got)\b", re.I)
_PROPOSAL_HEAD = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]*|\*\*|h\d\.[ \t]*)?(?:fix[ \t]+proposals?|suggestions?"
    r"|proposed[ \t]+(?:solution|fix)|expected[ \t]+results?)\b[^\n]*$",
    re.I | re.M,
)
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n")

# What makes an actual result concrete without reading it: a screenshot, a log or a
# trace, an error name or status, quoted text, a wrong value, a crash or a hang.
_CONCRETE = [
    re.compile(
        r"^\s*at\s+[\w$.<>]+\(|Traceback \(most recent|^\s*File \".+\", line \d+"
        r"|\b\w+(?:Exception|Error)\b(?::|\s+at\b)|^\s*Caused by:",
        re.M,
    ),
    re.compile(r"\b[A-Z]\w*(?:Exception|Error)\b|\bNPE\b|\bsegfault\b", re.I),
    re.compile(
        r"\b(?:HTTP\s*)?[45]\d\d\b(?=\s*(?:error|status|response|code|\(|$))"
        r"|\b[45]\d\d\s+(?:Not Found|Internal|Bad|Forbidden|Unauthorized)",
        re.I,
    ),
    # An apostrophe in "doesn't … doesn't" is not a quote.
    re.compile(r"\"[^\"\n]{4,}\"|(?<![A-Za-z])'[^'\n]{8,}'|“[^”\n]{4,}”|`[^`\n]+`"),
    re.compile(
        r"\binstead\s+of\b|\b(?:returns?|returned|shows?|showed|shown|displays?"
        r"|displayed|gives?|gave|prints?|printed|outputs?)\s+(?:an?\s+|the\s+)?"
        r"(?:null|empty|blank|nothing|zero|0|-?\d[\d.,]*|true|false|undefined|NaN"
        r"|wrong|incorrect)"
        r"|\bis\s+(?:null|empty|blank|undefined|missing"
        r"|not\s+(?:shown|displayed|saved|updated))\b",
        re.I,
    ),
    re.compile(
        r"\b(?:crash(?:es|ed|ing)?|hang(?:s|ing)?|hung|freez(?:es|ing)|froze(?:n)?"
        r"|deadlock|infinite\s+loop|blank\s+(?:page|screen)|white\s+screen"
        r"|out\s+of\s+memory|OOM)\b",
        re.I,
    ),
]
# Without a marker, a result in these words is not concrete (Max: "red errors on UI
# page", "doesn't work"); a prose symptom without them is ("the header lacks the port").
_VAGUE_RESULT = re.compile(
    r"\b(?:does\s*n[o']?t|do\s*n[o']?t|wo\s*n't|will\s+not|is\s*n't|is\s+not)\s+work"
    r"|\bnot\s+working\b|\bbroken\b|\bfail(?:s|ed|ing|ure)?\b|\berrors?\b"
    r"|\bproblems?\b|\bissues?\b|\bwrong\b|\bincorrect(?:ly)?\b|\bnothing\s+happens\b",
    re.I,
)
_WORD = re.compile(r"[A-Za-z]{2,}")


def _prose(description: str) -> str:
    """Without code blocks: an `expected ';'` in a log is not a claim."""
    return _CODE_BLOCK.sub(" ", description)


def _strict_steps(description: str) -> bool:
    """A list of 2+ items, a filled Steps section, code, a command or a menu path.
    A walk-through in prose does not count: no verb list tells actions apart."""
    prose = _prose(description)
    return bool(
        _CODE_BLOCK.search(description)
        or _COMMAND.search(description)
        or any(
            f == "steps" and not _BLANK.fullmatch(c) for f, c in _sections(description)
        )
        or len(_LIST_ITEM.findall(prose)) >= 2
        or _MENU_PATH.search(prose)
    )


def _strict_expected(description: str) -> bool:
    """Stated, not implied: a section, a "should"-word or an assertion. A heading
    names a field and a question asks, so neither states anything."""
    if any(
        f == "expected" and not _BLANK.fullmatch(c) for f, c in _sections(description)
    ):
        return True
    for m in _PROPOSAL_HEAD.finditer(description):
        rest = description[m.end() :].strip()
        if rest and not _BLANK.fullmatch(rest.split("\n", 1)[0]):
            return True
    if _ASSERT.search(description):
        return True
    lines = [ln for ln in _prose(description).split("\n") if not _section_head(ln)]
    sentences = _SENTENCE.split("\n".join(lines))
    return any(
        _EXPECT_WORDS.search(s) for s in sentences if not s.rstrip().endswith("?")
    )


def _result_text(description: str) -> str:
    """Prose outside the Steps / Expected sections: where a result could be. A
    Steps list ends at the first unindented line that is not an item: authors
    often write the result right after the steps, with no heading of its own."""
    keep, skip, steps, listed = [], False, False, False
    for line in _prose(description).split("\n"):
        head = _section_head(line)
        if head:
            steps = head[3].lower() == "steps"
            skip = steps or head[3].lower() == "expected"
            listed = False
            if not skip:
                keep.append(head[7])
        elif _ANY_HEAD.match(line):
            skip = False
        elif steps and skip and _LIST_ITEM.match(line):
            listed = True
        elif steps and skip and listed and line.strip() and line == line.lstrip():
            skip = False
            keep.append(line)
        elif not skip:
            keep.append(line)
    return "\n".join(keep)


def _strict_actual(description: str) -> bool:
    """Missing only when nothing concrete is found and the result is absent or
    vague: "concrete" is semantic, so the rule stays narrow (D26 measurement)."""
    if "[image]" in description or _CODE_BLOCK.search(description):
        return True
    prose = _prose(description)
    if any(p.search(prose) for p in _CONCRETE):
        return True
    text = _result_text(description)
    return len(_WORD.findall(text)) >= 3 and not _VAGUE_RESULT.search(text)


def strict_missing(state: dict[str, str]) -> list[str]:
    """Steps / expected / actual the description does not state by the strict
    criteria, whatever the summary says."""
    d = state["description"]
    checks = {
        "steps": _strict_steps,
        "expected": _strict_expected,
        "actual": _strict_actual,
    }
    return [c for c, stated in checks.items() if not stated(d)]
