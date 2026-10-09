"""The bot's comment on a bug report, in markdown.

Only blockers decide whether a report is complete; hints are soft and folded away.
A check the model is unsure of gets no verdict: a blocker is listed as "not sure",
a hint is simply not given.
"""

from bug_report_checker.decide import BLOCKERS, MISSING, UNSURE, Decision

NAMES = {
    "steps": "Steps to reproduce",
    "expected": "Expected result",
    "actual": "Actual result",
    "build_version": "Build version",
}
HOW_TO_FIX = {
    "steps": "list the steps that lead to the problem. If they are unknown,"
    " describe the conditions in which it happened.",
    "expected": "describe what should have happened.",
    "actual": "describe what happened instead: the symptom, error or wrong value.",
    "build_version": "name the exact build where you saw the bug,"
    " not latest or the current prod.",
}
HINTS = {
    "summary_what": "Say in the title what is wrong, not what to do.",
    "summary_where": "Name in the title where it happens: a screen, feature"
    " or component.",
    "summary_when": "Name in the title when it happens: the action or condition.",
}
IMAGE_ONLY = "Describe the {} result in text too, not only as a screenshot."


def is_complete(d: Decision) -> bool:
    return all(d.verdicts[c] not in (MISSING, UNSURE) for c in BLOCKERS)


def render(d: Decision, status: str) -> str:
    missing = [c for c in BLOCKERS if d.verdicts[c] == MISSING]
    unsure = [c for c in BLOCKERS if d.verdicts[c] == UNSURE]
    hints = [text for c, text in HINTS.items() if d.verdicts[c] == MISSING]
    hints += [IMAGE_ONLY.format(field) for field in d.image_only]

    if missing:
        parts = ["**Some details are missing from this bug report.**"]
        items = [f"- **{NAMES[c]}**: {HOW_TO_FIX[c]}" for c in missing]
        parts.append("\n".join(["Missing:", *items]))
    elif unsure:
        parts = ["**Could not check everything in this bug report.**"]
    else:
        parts = ["✅ **Bug report complete.**"]
    if unsure:
        names = ", ".join(f"**{NAMES[c]}**" for c in unsure)
        them = "them" if len(unsure) > 1 else "it"
        parts.append(f"Not sure about: {names}. Please check {them} yourself.")
    if d.long:
        parts.append(
            "This report is long and was read in parts, so details found in it"
            " could not be confirmed."
        )
    if hints:
        items = "\n".join(f"- {h}" for h in hints)
        parts.append(
            f"<details>\n<summary>Suggestions ({len(hints)})</summary>\n\n"
            f"{items}\n\n</details>"
        )
    footer = f"Checked in status **{status}** by bug-report-checker."
    if d.environments:
        footer += f" Environment: {', '.join(d.environments)}."
    parts.append(f"<sub>{footer}</sub>")
    return "\n\n".join(parts)
