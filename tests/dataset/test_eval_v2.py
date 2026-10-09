import random

import pytest

from bug_report_checker.dataset.eval_v2 import check_unused, sample, select


def _cand(key, project="P1", tracker="Apache", tokens=100):
    return {
        "key": key,
        "tracker": tracker,
        "project": project,
        "summary": f"Crash {key}",
        "description": "It crashes.",
        "tokens": tokens,
        "flags": {"steps": False},
    }


def _labels(rows, missing):
    """Every check present except `missing[id]` (a set of check names)."""
    return {
        r["id"]: {
            "actual": "actual" not in missing.get(r["id"], ()),
            "expected": "expected" not in missing.get(r["id"], ()),
        }
        for r in rows
    }


def test_sample_skips_used_projects_and_sets_a_random_core_aside():
    cands = [_cand(f"A-{i}", project=f"P{i % 4}") for i in range(40)]
    cands += [_cand(f"L-{i}", project=f"P{i % 4}", tokens=2000) for i in range(10)]

    pool = sample(
        cands,
        used_projects={("Apache", "P0")},
        sizes=(12, 3),
        core_sizes=(4, 1),
        rng=random.Random(0),
    )

    assert len(pool) == 15
    assert all(r["project"] != "P0" for r in pool)
    core = [r for r in pool if r["core"]]
    assert len(core) == 5
    assert sum(r["id"].startswith("Apache:L-") for r in core) == 1


def test_select_keeps_the_core_and_adds_only_reports_with_a_gap():
    pool = [
        {"id": "core-1", "core": True},
        {"id": "core-2", "core": True},
        {"id": "full", "core": False},
        {"id": "no-actual", "core": False},
        {"id": "no-expected", "core": False},
    ]
    labels = _labels(pool, {"no-actual": {"actual"}, "no-expected": {"expected"}})

    chosen = select(pool, labels, n_extra=5, rng=random.Random(0))

    assert {r["id"] for r in chosen} == {"core-1", "core-2", "no-actual", "no-expected"}


def test_select_fills_half_the_extras_with_missing_actual_first():
    pool = [{"id": f"a{i}", "core": False} for i in range(10)]
    pool += [{"id": f"e{i}", "core": False} for i in range(10)]
    missing = {f"a{i}": {"actual"} for i in range(10)}
    missing |= {f"e{i}": {"expected"} for i in range(10)}

    chosen = select(pool, _labels(pool, missing), n_extra=6, rng=random.Random(0))

    assert sum(r["id"].startswith("a") for r in chosen) == 3
    assert sum(r["id"].startswith("e") for r in chosen) == 3


def test_select_tops_up_from_missing_actual_when_expected_runs_short():
    pool = [{"id": f"a{i}", "core": False} for i in range(10)]
    pool += [{"id": "e0", "core": False}]
    missing = {f"a{i}": {"actual"} for i in range(10)} | {"e0": {"expected"}}

    chosen = select(pool, _labels(pool, missing), n_extra=6, rng=random.Random(0))

    assert len(chosen) == 6
    assert "e0" in {r["id"] for r in chosen}


def test_check_unused_rejects_a_project_from_another_set():
    eval_v2 = [{"tracker": "Apache", "project": "P1"}]

    check_unused(eval_v2, [{"tracker": "Apache", "project": "P2"}])
    with pytest.raises(ValueError, match="P1"):
        check_unused(eval_v2, [{"tracker": "Apache", "project": "P1"}])
