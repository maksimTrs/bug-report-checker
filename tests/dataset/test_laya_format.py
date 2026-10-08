import pytest
from laya.train import target_from_gold, to_internal

from bug_report_checker.dataset.laya_format import to_laya_rows
from bug_report_checker.labeling import CHECKS
from bug_report_checker.questions import QUESTIONS, laya_questions


def _report(id_="Apache:X-1"):
    return {
        "id": id_,
        "source": "public",
        "tracker": "Apache",
        "project": "X",
        "summary": "Crash on save",
        "description": "1. Open\n2. Save",
    }


def _labels(id_="Apache:X-1", **overrides):
    return {"id": id_, **dict.fromkeys(CHECKS, True), **overrides}


def test_questions_cover_every_check():
    assert tuple(QUESTIONS) == CHECKS


def test_row_has_state_questions_and_hard_gold():
    [row] = to_laya_rows([_report()], [_labels(steps=False)])

    assert row["id"] == "Apache:X-1"
    assert row["state"] == {
        "summary": "Crash on save",
        "description": "1. Open\n2. Save",
    }
    assert row["questions"] == laya_questions()
    assert row["gold"]["steps"] == {
        "probabilities": {"false": 1.0, "true": 0.0},
        "label": False,
    }
    assert row["gold"]["actual"]["probabilities"] == {"false": 0.0, "true": 1.0}


def test_laya_accepts_every_question_and_target():
    [row] = to_laya_rows([_report()], [_labels(expected=False)])

    for qid, question in row["questions"].items():
        q = to_internal(qid, question)
        target = target_from_gold(q, row["gold"][qid])
        assert target == ([0.0, 1.0] if row["gold"][qid]["label"] else [1.0, 0.0])


def test_labels_are_matched_by_id():
    rows = to_laya_rows(
        [_report("a"), _report("b")], [_labels("b", steps=False), _labels("a")]
    )

    assert [r["gold"]["steps"]["label"] for r in rows] == [True, False]


def test_report_without_labels_fails():
    with pytest.raises(ValueError, match="no labels for \\['b'\\]"):
        to_laya_rows([_report("a"), _report("b")], [_labels("a")])


def test_smoothing_softens_targets_and_keeps_the_label():
    [row] = to_laya_rows([_report()], [_labels(steps=False)], smoothing=0.1)

    assert row["gold"]["steps"]["probabilities"] == {"false": 0.95, "true": 0.05}
    assert row["gold"]["steps"]["label"] is False
    assert row["gold"]["actual"]["probabilities"] == {"false": 0.05, "true": 0.95}
