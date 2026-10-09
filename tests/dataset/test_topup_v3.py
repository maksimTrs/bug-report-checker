import random

from bug_report_checker.dataset.topup_v3 import ordinary_gap, select, split

LONG = "The export job writes rows. " * 20


def _cand(key, summary="Export fails", description=LONG, tokens=200, **kw):
    return {
        "key": key,
        "tracker": "Apache",
        "project": "P1",
        "summary": summary,
        "description": description,
        "tokens": tokens,
        **kw,
    }


def test_short_report_is_a_candidate():
    assert ordinary_gap("Export is slow", "Very slow on big files.", tokens=20)


def test_long_report_with_a_result_is_not():
    text = LONG + "It throws an error instead of saving."
    assert not ordinary_gap("Export fails on save", text, tokens=200)


def test_task_like_summary_is_left_to_the_run_2_top_up():
    assert not ordinary_gap("Add retry to export", "Please add it.", tokens=20)


def test_description_that_restates_the_summary_is_a_candidate():
    assert ordinary_gap("Export drops rows", "Export drops rows\n\n" + LONG, tokens=200)


def test_steps_without_any_result_are_a_candidate():
    steps = "1. Open the export page\n2. Pick a date range\n3. Press Export\n" + LONG
    assert ordinary_gap("Export of a date range", steps, tokens=200)
    assert not ordinary_gap("Export of a date range", steps + "It fails.", tokens=200)


def test_select_skips_used_ids_and_excluded_projects():
    cands = [
        _cand("A-1", tokens=20),
        _cand("A-2", tokens=20, project="EVAL"),
        _cand("A-3", tokens=20),
        _cand("A-4"),  # long, with no gap signal
        _cand("A-5", tokens=900),
    ]

    picked = select(
        cands,
        used_ids={"Apache:A-3"},
        excluded_projects={("Apache", "EVAL")},
        n=10,
        rng=random.Random(0),
    )

    assert [c["key"] for c in picked] == ["A-1"]


def test_select_spreads_seats_by_sqrt_of_tracker_size():
    cands = [_cand(f"M-{i}", tokens=20, tracker="Mojang") for i in range(90)]
    cands += [_cand(f"A-{i}", tokens=20) for i in range(10)]

    picked = select(cands, set(), set(), n=8, rng=random.Random(0))

    trackers = [c["tracker"] for c in picked]
    assert len(picked) == 8
    assert trackers.count("Mojang") == 6 and trackers.count("Apache") == 2


def test_split_keeps_two_thirds_for_train_and_does_not_overlap():
    rows = [{"id": f"r{i}"} for i in range(9)]

    train, dev = split(rows, rng=random.Random(0))

    assert len(train) == 6 and len(dev) == 3
    assert not {r["id"] for r in train} & {r["id"] for r in dev}
