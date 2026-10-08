import pytest

from bug_report_checker.dataset.assemble import FIELDS, assemble, validate


def _public(i, project="P1", tracker="Apache"):
    return {
        "key": f"{project}-{i}",
        "tracker": tracker,
        "project": project,
        "summary": f"[UI] Save fails {i}",
        "description": "h3. Steps\r\n# Click *Save*",
    }


def _synthetic(id_, area="Billing"):
    return {
        "id": id_,
        "summary": "[Billing] Refund fails",
        "description": "**Build version:** 2026.10-rc-1\n\n# Steps",
        "area": area,
    }


SIZES = {"train": (2, 1), "eval": (1, 0), "style_eval": (0, 1)}


def _sets():
    return assemble(
        public_train=[_public(1), _public(2)],
        public_eval=[_public(3, project="P2")],
        synthetic=[_synthetic("syn-train-001"), _synthetic("syn-style-001")],
        seed=1,
    )


def test_assemble_preprocesses_by_source_and_maps_fields():
    sets = _sets()
    assert set(sets) == {"train", "eval", "style_eval"}
    public = next(r for r in sets["train"] if r["source"] == "public")
    assert set(public) == set(FIELDS)
    assert public["id"].startswith("Apache:P1-")
    assert public["summary"].startswith("Save fails")
    assert public["description"] == "### Steps\n1. Click **Save**"
    (style,) = sets["style_eval"]
    assert style == {
        "id": "syn-style-001",
        "source": "synthetic",
        "tracker": "Parcelwise",
        "project": "Billing",
        "summary": "Refund fails",
        "description": "**Build version:** 2026.10-rc-1\n\n# Steps",
    }


def test_assemble_is_deterministic():
    assert _sets() == _sets()


def test_validate_accepts_expected_sizes():
    validate(_sets(), SIZES)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda s: s["train"].pop(), "train"),
        (lambda s: s["eval"].append(dict(s["train"][0])), "duplicate"),
        (lambda s: s["eval"][0].update(project="P1"), "both train and eval"),
        (lambda s: s["style_eval"][0].update(summary=" "), "empty"),
        (lambda s: s["style_eval"][0].update(extra=1), "fields"),
    ],
)
def test_validate_rejects_broken_sets(mutate, message):
    sets = _sets()
    mutate(sets)
    with pytest.raises(ValueError, match=message):
        validate(sets, SIZES)
