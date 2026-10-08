import pytest

from bug_report_checker.labeling import CHECKS
from bug_report_checker.labeling.agreement import agreement, report


def _row(id_, **overrides):
    return {"id": id_, **dict.fromkeys(CHECKS, True), **overrides}


def test_counts_agreement_per_check():
    reference = [_row("a"), _row("b", steps=False), _row("c", steps=False)]
    labels = [_row("a"), _row("b", steps=False), _row("c")]

    stats = agreement(reference, labels)

    assert stats["steps"]["agree"] == 2
    assert stats["actual"]["agree"] == 3
    assert all(s["n"] == 3 for s in stats.values())


def test_minority_class_comes_from_reference():
    reference = [_row("a"), _row("b"), _row("c", actual=False)]
    labels = [_row("a"), _row("b"), _row("c")]

    s = agreement(reference, labels)["actual"]

    assert (s["minority"], s["minority_n"], s["minority_agree"]) == (False, 1, 0)


def test_tie_takes_no_as_minority():
    stats = agreement([_row("a"), _row("b", steps=False)], [_row("a"), _row("b")])

    assert stats["steps"]["minority"] is False


def test_rows_are_matched_by_id_not_order():
    reference = [_row("a", steps=False), _row("b")]
    labels = [_row("b"), _row("a", steps=False)]

    assert agreement(reference, labels)["steps"]["agree"] == 2


def test_different_ids_fail():
    with pytest.raises(ValueError, match="missing: \\['b'\\].*extra: \\['c'\\]"):
        agreement([_row("a"), _row("b")], [_row("a"), _row("c")])


def test_report_fails_below_threshold():
    reference = [_row(str(i)) for i in range(20)]
    labels = [_row(str(i), steps=i >= 4) for i in range(20)]  # 16/20 on steps

    table, ok = report(agreement(reference, labels), min_share=0.85)

    assert not ok
    assert "| steps | 16/20 FAIL |" in table


def test_report_passes_at_threshold():
    reference = [_row(str(i)) for i in range(20)]
    labels = [_row(str(i), steps=i >= 3) for i in range(20)]  # 17/20

    assert report(agreement(reference, labels), min_share=0.85)[1]
