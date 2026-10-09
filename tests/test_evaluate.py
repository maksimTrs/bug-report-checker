import pytest

from bug_report_checker.evaluate import bot_metrics, check_metrics, wilson


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


def test_bot_says_not_sure_below_the_threshold():
    # gold: missing, missing, present, present
    gold = [False, False, True, True]
    p_true = [0.05, 0.4, 0.95, 0.2]  # confidence 0.95, 0.6, 0.95, 0.8

    m = bot_metrics(gold, p_true, threshold=0.75)

    assert m["coverage"] == pytest.approx(0.75)  # 0.6 is "not sure"
    assert m["accuracy_decided"] == pytest.approx(2 / 3)
    assert (m["no_said_no"], m["no_unsure"], m["no_said_yes"]) == (1, 1, 0)
    assert m["yes_said_no"] == 1


def test_bot_without_decisions_has_no_accuracy():
    m = bot_metrics([True], [0.6], threshold=0.9)

    assert m["coverage"] == 0.0
    assert m["accuracy_decided"] is None


def _gate_case(found_old, found_new, false_alarm_new=()):
    """Ten reports, the first five missing every part; models find the given rows."""
    from bug_report_checker.labeling import CHECKS

    rows = [{"id": str(i), **{c: i >= 5 for c in CHECKS}} for i in range(10)]

    def preds(found):
        return [
            {"id": str(i), **{c: 0.1 if i in found.get(c, ()) else 0.9 for c in CHECKS}}
            for i in range(10)
        ]

    everywhere = dict.fromkeys(CHECKS)
    old = preds({c: found_old for c in everywhere})
    new = preds({c: found_new for c in everywhere} | dict(false_alarm_new))
    return rows, old, new


def test_gate_passes_when_actual_and_expected_improve_and_nothing_drops():
    from bug_report_checker.evaluate import gate

    assert gate(*_gate_case({0, 1}, {0, 1, 2})) == []


def test_gate_fails_when_actual_does_not_improve():
    from bug_report_checker.evaluate import gate

    rows, old, new = _gate_case({0, 1}, {0, 1, 2})
    for p_old, p_new in zip(old, new, strict=True):
        p_new["actual"] = p_old["actual"]

    assert any("actual" in reason for reason in gate(rows, old, new))


def test_gate_fails_when_a_check_loses_precision():
    from bug_report_checker.evaluate import gate

    case = _gate_case({0, 1}, {0, 1, 2}, {"steps": {0, 1, 2, 5}})

    assert any(reason.startswith("steps") for reason in gate(*case))


def test_gate_fails_on_more_false_missing_among_the_random_reports():
    from bug_report_checker.evaluate import gate

    # one more complete report called "missing" on steps: 1 of 5 present = 20 points
    rows, old, new = _gate_case({0, 1}, {0, 1, 2}, {"steps": {0, 1, 2, 5}})
    random_ids = {r["id"] for r in rows}

    reasons = gate(rows, old, new, random_ids)

    assert "steps: false missing on present rose by 20.0 points" in reasons


def test_gate_counts_false_missing_only_on_the_random_reports():
    from bug_report_checker.evaluate import gate

    rows, old, new = _gate_case({0, 1}, {0, 1, 2}, {"steps": {0, 1, 2, 5}})

    reasons = gate(rows, old, new, random_ids={"0", "6"})

    assert not any("false missing" in reason for reason in reasons)
