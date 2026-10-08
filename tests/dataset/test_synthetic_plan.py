import pytest

from bug_report_checker.dataset.synthetic_plan import (
    INCOMPATIBLE,
    TRAIN_MIN,
    build_specs,
    coverage,
    parse_batch,
    validate_records,
)

TRAIN_CODES = {
    "full", "build_empty", "build_os", "build_moving", "steps_unknown", "image_only",
    "expected_question", "expected_struck", "free_one_line", "free_trace",
    "links_tables", "tag_summary", "task_summary",
}  # fmt: skip


def test_train_covers_every_variation_at_least_min_times():
    train, _ = build_specs()
    counts = coverage(train)
    assert len(train) == 80
    assert set(counts) == TRAIN_CODES
    assert min(counts.values()) >= TRAIN_MIN


def test_style_eval_has_long_specs_and_every_code():
    _, style = build_specs()
    counts = coverage(style)
    assert len(style) == 30
    assert counts["spec_long"] == 3
    assert set(counts) == TRAIN_CODES | {"spec_long"}


def test_specs_unique_ids_no_conflicts_and_deterministic():
    train, style = build_specs()
    ids = [s["id"] for s in train + style]
    assert len(ids) == len(set(ids))
    for spec in train + style:
        codes = set(spec["variations"])
        assert 1 <= len(codes) <= 3
        assert not any(pair <= codes for pair in INCOMPATIBLE), spec
        assert (spec["image_only_field"] is not None) == ("image_only" in codes)
    assert build_specs() == (train, style)


def _record(
    id_, description="Steps: open [stand](https://dev1.parcelwise.example.com)"
):
    return {
        "id": id_,
        "summary": "Invoice PDF shows wrong VAT",
        "description": description,
    }


def test_validate_records_accepts_matching_ids():
    specs = [{"id": "syn-001"}, {"id": "syn-002"}]
    validate_records(specs, [_record("syn-001"), _record("syn-002")])


@pytest.mark.parametrize(
    ("records", "message"),
    [
        ([_record("syn-001")], "missing"),
        ([_record("syn-001"), _record("syn-002"), _record("syn-003")], "unexpected"),
        (
            [_record("syn-001"), _record("syn-002", "See https://grafana.acme.io/d/1")],
            "host",
        ),
        ([_record("syn-001"), _record("syn-002", "variation build_os here")], "code"),
        ([_record("syn-001"), _record("syn-002", "  ")], "empty"),
    ],
)
def test_validate_records_rejects_bad_batches(records, message):
    with pytest.raises(ValueError, match=message):
        validate_records([{"id": "syn-001"}, {"id": "syn-002"}], records)


def test_parse_batch_splits_blocks_and_keeps_markdown():
    text = (
        "@@@ syn-train-001\n"
        "Fix webhook retries\n"
        "@@@\n"
        "**Build version:** current prod\n"
        "\n"
        "Logs @@@ inline stay\n"
        "\n"
        "@@@ syn-train-002\n"
        "Export has no header\n"
        "@@@\n"
        "One line.\n"
    )
    assert parse_batch(text) == [
        {
            "id": "syn-train-001",
            "summary": "Fix webhook retries",
            "description": "**Build version:** current prod\n\nLogs @@@ inline stay",
        },
        {
            "id": "syn-train-002",
            "summary": "Export has no header",
            "description": "One line.",
        },
    ]
