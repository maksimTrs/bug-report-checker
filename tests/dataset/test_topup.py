import random

from bug_report_checker.dataset.topup import likely_missing, select


def _cand(key, summary="Crash on save", description="It crashes.", project="P1", **kw):
    return {
        "key": key,
        "tracker": "Apache",
        "project": project,
        "summary": summary,
        "description": description,
        "tokens": 100,
        **kw,
    }


def test_no_expected_words_suggests_missing_expected():
    assert "expected" in likely_missing("Crash on save", "It crashes on save.")
    assert "expected" not in likely_missing("Crash", "It should save the file.")


def test_task_summary_suggests_missing_actual():
    assert "actual" in likely_missing("Add retry to label printing", "Please add it.")
    assert "actual" in likely_missing("Does Nexus support TLS 1.2?", "Asking.")
    assert "actual" not in likely_missing("Label printing fails", "It fails.")


def test_select_skips_eval_projects_used_ids_and_long_reports():
    cands = [
        _cand("A-1"),
        _cand("A-2", project="EVAL"),
        _cand("A-3", tokens=900),
        _cand("A-4"),
        _cand("A-5"),
    ]

    train, dev, mine = select(
        cands,
        used_ids={"Apache:A-4"},
        eval_projects={("Apache", "EVAL")},
        sizes=(1, 1, 0, 5),
        rng=random.Random(0),
    )

    picked = {c["key"] for c in train + dev + mine}
    assert picked == {"A-1", "A-5"}


def test_train_and_dev_do_not_overlap():
    cands = [_cand(f"A-{i}") for i in range(20)]

    train, dev, _ = select(
        cands, set(), set(), sizes=(8, 4, 4, 0), rng=random.Random(0)
    )

    assert len(train) == 8 and len(dev) == 8
    assert not {c["key"] for c in train} & {c["key"] for c in dev}


def test_mine_takes_task_like_reports_left_over():
    cands = [_cand("A-1"), _cand("A-2", summary="Add retry to printing")]

    train, dev, mine = select(
        cands, set(), set(), sizes=(0, 0, 0, 5), rng=random.Random(0)
    )

    assert (train, dev) == ([], [])
    assert [c["key"] for c in mine] == ["A-2"]


def test_mined_reports_kept_only_without_actual_and_split():
    from bug_report_checker.dataset.topup import split_mined

    rows = [{"id": f"m{i}"} for i in range(9)]
    labels = {f"m{i}": {"actual": i % 3 != 0} for i in range(9)}  # 3 lack actual

    train, dev = split_mined(rows, labels, rng=random.Random(0))

    assert len(train) == 2 and len(dev) == 1
    assert all(not labels[r["id"]]["actual"] for r in train + dev)
