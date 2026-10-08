import pytest

from bug_report_checker.evaluate import check_metrics, wilson


def test_wilson_interval_contains_the_share():
    low, high = wilson(8, 10)

    assert low < 0.8 < high
    assert (round(low, 3), round(high, 3)) == (0.49, 0.943)


def test_wilson_stays_within_zero_and_one():
    assert wilson(0, 30)[0] == 0.0
    assert wilson(30, 30)[1] == 1.0


def test_wilson_of_nothing_is_undefined():
    assert wilson(0, 0) == (None, None)


def test_metrics_count_missing_parts_as_the_positive_class():
    # gold: two "missing", two "present"; model finds one of the missing ones
    gold = [False, False, True, True]
    p_true = [0.1, 0.8, 0.9, 0.3]

    m = check_metrics(gold, p_true)

    assert m["n"] == 4
    assert m["accuracy"] == pytest.approx(0.5)
    assert (m["no_n"], m["no_found"]) == (2, 1)
    assert m["recall_no"] == pytest.approx(0.5)
    assert m["precision_no"] == pytest.approx(0.5)  # 1 of 2 "missing" answers right


def test_no_missing_predictions_leave_precision_undefined():
    m = check_metrics([True, False], [0.9, 0.7])

    assert m["recall_no"] == 0.0
    assert m["precision_no"] is None


def test_confidence_is_of_the_chosen_answer():
    m = check_metrics([True, False], [0.9, 0.2])

    assert m["mean_confidence"] == pytest.approx(0.85)
