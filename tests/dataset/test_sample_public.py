import random

import pytest

from bug_report_checker.dataset.sample_public import (
    ROOM,
    check_disjoint,
    flags,
    sample,
    split_projects,
    tracker_quotas,
)


def _cand(i, tracker, project, tokens, rare=False):
    return {
        "key": f"{project}-{i}",
        "tracker": tracker,
        "project": project,
        "tokens": tokens,
        "flags": {
            "steps": rare,
            "expected": False,
            "version": False,
            "template": False,
        },
    }


def _pool():
    rng = random.Random(1)
    cands = []
    for tracker, projects in {"A": 8, "B": 4, "C": 3}.items():
        for p in range(projects):
            for i in range(60):
                tokens = rng.choice([20, 120, 400, 2000])
                cands.append(_cand(i, tracker, f"{tracker}P{p}", tokens, i % 7 == 0))
    return cands


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        (
            "### Steps to reproduce\n1. Open\n### Expected result\nOK\n### Actual\nKO",
            {"steps": True, "expected": True, "version": False, "template": True},
        ),
        (
            "1. Open the app\n2. Click Save\nIt crashes on 2.4.1",
            {"steps": True, "expected": False, "version": True, "template": False},
        ),
        (
            "It crashes. Expected: no crash. Build 1874.",
            {"steps": False, "expected": True, "version": True, "template": False},
        ),
        (
            "Takes 1.5 seconds",
            {"steps": False, "expected": False, "version": False, "template": False},
        ),
    ],
)
def test_flags_detect_rare_parts(description, expected):
    assert flags(description) == expected


def test_tracker_quotas_sqrt_proportional_with_minimum_and_exact_total():
    quotas = tracker_quotas({"big": 10_000, "mid": 900, "tiny": 1}, total=50, minimum=2)
    assert sum(quotas.values()) == 50
    assert quotas["tiny"] == 2
    assert quotas["big"] > quotas["mid"] > quotas["tiny"]


def test_split_projects_is_deterministic_and_leaves_train_projects():
    cands = _pool()
    first = split_projects(cands, 0.3, random.Random(7))
    assert first == split_projects(cands, 0.3, random.Random(7))
    for tracker in "ABC":
        projects = {c["project"] for c in cands if c["tracker"] == tracker}
        assert 0 < len(projects & {p for t, p in first if t == tracker}) < len(projects)


def test_sample_sizes_projects_and_lengths():
    train, eval_ = sample(_pool(), seed=3, sizes=(40, 18, 2))
    assert (len(train), len(eval_)) == (40, 20)
    check_disjoint(train, eval_)
    assert all(c["tokens"] <= ROOM for c in train)
    assert sum(c["tokens"] > ROOM for c in eval_) == 2
    assert {c["tracker"] for c in train} == {"A", "B", "C"}


def test_sample_is_deterministic_for_a_seed():
    keys = [[c["key"] for c in part] for part in sample(_pool(), 3, (40, 18, 2))]
    again = [[c["key"] for c in part] for part in sample(_pool(), 3, (40, 18, 2))]
    assert keys == again


def test_check_disjoint_fails_on_shared_project():
    train = [_cand(1, "A", "AP0", 20)]
    with pytest.raises(ValueError, match="AP0"):
        check_disjoint(train, [_cand(2, "A", "AP0", 20)])
