import gzip
import io
import json
import struct
import zipfile

import bson
import pytest

from bug_report_checker.dataset.jira_dump import (
    DUMP_PATH,
    ArchiveError,
    extract,
    iter_documents,
    to_record,
)

TERMINATOR = struct.pack("<i", -1)


def _archive(blocks: list[tuple[str, list[dict], bool]]) -> bytes:
    """Build a mongodump archive: magic, prelude, (collection, docs, eof) blocks."""
    collections = sorted({name for name, _, _ in blocks})
    out = [struct.pack("<I", 0x8199E26D), bson.encode({"version": "0.1"})]
    out += [bson.encode({"db": "JiraReposAnon", "collection": c}) for c in collections]
    out.append(TERMINATOR)
    for name, docs, eof in blocks:
        header = {"db": "JiraReposAnon", "collection": name, "EOF": eof, "CRC": 0}
        out.append(bson.encode(header))
        out += [bson.encode(d) for d in docs]
        out.append(TERMINATOR)
    return b"".join(out)


def _issue(key: str, **fields) -> dict:
    return {"id": key.split("-")[1], "key": key, "fields": fields, "changelog": {}}


def test_iter_documents_follows_interleaved_blocks_and_skips_eof_blocks():
    raw = _archive(
        [
            ("Apache", [_issue("A-1"), _issue("A-2")], False),
            ("Qt", [_issue("Q-1")], False),
            ("Apache", [_issue("A-3")], False),
            ("Apache", [], True),
            ("Qt", [], True),
        ]
    )

    docs = [(c, bson.decode(d)["key"]) for c, d in iter_documents(io.BytesIO(raw))]

    assert docs == [
        ("Apache", "A-1"),
        ("Apache", "A-2"),
        ("Qt", "Q-1"),
        ("Apache", "A-3"),
    ]


def test_iter_documents_rejects_wrong_magic():
    with pytest.raises(ArchiveError, match="not a mongodump archive"):
        list(iter_documents(io.BytesIO(b"\x00\x00\x00\x00")))


def test_iter_documents_rejects_truncated_archive():
    raw = _archive([("Qt", [_issue("Q-1")], False)])

    with pytest.raises(ArchiveError, match="unexpected end"):
        list(iter_documents(io.BytesIO(raw[:-10])))


def test_to_record_keeps_only_needed_fields():
    doc = _issue(
        "QTBUG-7",
        summary="Crash on start",
        description="Steps: ...",
        issuetype={"id": "1", "name": "Bug", "iconUrl": "x"},
        project={"key": "QTBUG", "name": "Qt"},
        status={"name": "Open"},
        created="2021-05-01T10:00:00.000+0000",
        environment="Linux",
        versions=[{"name": "6.1.0"}, {"name": "6.2.0"}],
        customfield_10000="noise",
    )

    assert to_record("Qt", bson.encode(doc)) == {
        "tracker": "Qt",
        "id": "7",
        "key": "QTBUG-7",
        "project": "QTBUG",
        "issuetype_id": "1",
        "issuetype": "Bug",
        "status": "Open",
        "created": "2021-05-01T10:00:00.000+0000",
        "summary": "Crash on start",
        "description": "Steps: ...",
        "environment": "Linux",
        "versions": ["6.1.0", "6.2.0"],
    }


def test_to_record_tolerates_missing_fields():
    record = to_record("Qt", bson.encode({"id": "1", "key": "Q-1", "fields": {}}))

    assert record["issuetype"] is None
    assert record["description"] is None
    assert record["versions"] == []


def test_extract_writes_gzipped_jsonl_and_counts_per_tracker(tmp_path):
    archive = _archive(
        [
            ("Apache", [_issue("A-1"), _issue("A-2")], False),
            ("Qt", [_issue("Q-1")], False),
        ]
    )
    zip_path = tmp_path / "dataset.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(DUMP_PATH, gzip.compress(archive))
    out_path = tmp_path / "issues.jsonl.gz"

    counts = extract(zip_path, out_path)

    assert counts == {"Apache": 2, "Qt": 1}
    with gzip.open(out_path, "rt", encoding="utf-8") as fh:
        keys = [json.loads(line)["key"] for line in fh]
    assert keys == ["A-1", "A-2", "Q-1"]
