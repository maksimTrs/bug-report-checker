"""The seven yes / no questions the model answers about a bug report.

One definition for training, eval and the Action: the model is only reliable on the
exact wording it was fine-tuned on. Each is a condensed `labeling/rubric.md` check,
kept short — the question head and the report share one 1024-token sequence.
"""

PRESENT = {"true": "present", "false": "missing"}

QUESTIONS = {
    "summary_what": (
        "Does the summary name what is wrong: a faulty behaviour, not a task,"
        " a bare area or a vague 'does not work'?"
    ),
    "summary_where": (
        "Does the summary name a specific part of the product: a screen, feature,"
        " component, class or an object in it, not the whole product or a library?"
    ),
    "summary_when": (
        "Does the summary name the action or condition that triggers the problem?"
    ),
    "steps": (
        "Does the description give steps someone could follow to reproduce the problem:"
        " a list, a walk-through of actions, or a snippet or command to run?"
    ),
    "expected": (
        "Does the report state the expected result, or does it follow unambiguously"
        " from a crash, a hang, a failed run or a case that works?"
    ),
    "actual": (
        "Does the report state the actual result: a symptom, an error, a wrong value,"
        " a crash, a stack trace or a screenshot?"
    ),
    "build_version": (
        "Does the report name the concrete version, build or commit of the product"
        " where the bug was seen, not latest or master, not an OS or library version?"
    ),
}


def laya_questions() -> dict[str, dict]:
    """Questions in Laya's typed-decisions format: `noul`, P(true) is the answer."""
    return {
        qid: {"type": "noul", "instructions": text, "criteria": PRESENT}
        for qid, text in QUESTIONS.items()
    }
