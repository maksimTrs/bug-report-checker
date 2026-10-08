import pytest

from bug_report_checker.labeling import CHECKS
from bug_report_checker.labeling.teacher import check_labels, parse_answer


def _row(id_, **overrides):
    return {"id": id_, **dict.fromkeys(CHECKS, False), **overrides}


def test_valid_labels_pass():
    check_labels([_row("a"), _row("b", steps=True)], ["a", "b"])


def test_broken_json_names_the_line():
    with pytest.raises(ValueError, match="line 2: not JSON"):
        parse_answer('{"id": "a"}\n{"id": "b", steps: true}\n')


def test_line_that_is_not_an_object_fails():
    with pytest.raises(ValueError, match="line 1: not a JSON object"):
        parse_answer('["a"]\n')


def test_missing_key_fails():
    row = _row("a")
    del row["expected"]

    with pytest.raises(ValueError, match="a: missing keys \['expected'\]"):
        check_labels([row], ["a"])


def test_extra_key_fails():
    with pytest.raises(ValueError, match="a: extra keys \['reason'\]"):
        check_labels([_row("a", reason="x")], ["a"])


def test_non_boolean_value_fails():
    with pytest.raises(ValueError, match="a: steps is not true/false"):
        check_labels([_row("a", steps="true")], ["a"])


def test_foreign_id_fails():
    with pytest.raises(ValueError, match="unexpected ids \['z'\]"):
        check_labels([_row("a"), _row("z")], ["a"])


def test_missing_id_fails():
    with pytest.raises(ValueError, match="missing ids \['b'\]"):
        check_labels([_row("a")], ["a", "b"])


def test_duplicate_id_fails():
    with pytest.raises(ValueError, match="duplicate ids \['a'\]"):
        check_labels([_row("a"), _row("a")], ["a"])


def test_all_errors_are_reported_at_once():
    with pytest.raises(ValueError, match="extra keys.*missing ids"):
        check_labels([_row("a", reason="x")], ["a", "b"])
