"""Stream issues out of The Public Jira Dataset without restoring it into MongoDB.

The dataset ships as a gzipped `mongodump --archive` (~60 GB once restored), mostly
change history and comments we do not need. We read it straight from the Zenodo zip
and keep a few fields per issue.

Archive layout (mongo-tools `archive` package):
    magic, uint32 LE 0x8199e26d
    prelude: header BSON, one BSON per collection, terminator
    body: blocks of [namespace header BSON][document BSON ...][terminator]
A terminator is int32 -1. Blocks of different collections interleave.

Usage: python -m bug_report_checker.dataset.jira_dump <dataset.zip> <issues.jsonl.gz>
"""

import gzip
import io
import json
import struct
import sys
import time
import zipfile
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO

import bson
from bson.raw_bson import RawBSONDocument

MAGIC = 0x8199E26D
TERMINATOR = -1
DUMP_PATH = "ThePublicJiraDataset/3. DataDump/mongodump-JiraReposAnon.archive"
# Lazy decoding: nested documents (changelog, comments) stay raw bytes unless touched.
_RAW = bson.CodecOptions(document_class=RawBSONDocument)


class ArchiveError(ValueError):
    """The stream is not a well-formed mongodump archive."""


def _read_exact(stream: BinaryIO, n: int) -> bytes:
    data = stream.read(n)
    if len(data) != n:
        raise ArchiveError("unexpected end of archive")
    return data


def _read_bson(stream: BinaryIO, size_bytes: bytes) -> bytes | None:
    """Rest of a BSON document whose 4-byte size is already read; None on terminator."""
    if len(size_bytes) != 4:
        raise ArchiveError("unexpected end of archive")
    (size,) = struct.unpack("<i", size_bytes)
    if size == TERMINATOR:
        return None
    return size_bytes + _read_exact(stream, size - 4)


def iter_documents(stream: BinaryIO) -> Iterator[tuple[str, bytes]]:
    """Yield (collection, raw BSON document) for every document in the archive body."""
    if struct.unpack("<I", _read_exact(stream, 4))[0] != MAGIC:
        raise ArchiveError("not a mongodump archive")
    while _read_bson(stream, stream.read(4)) is not None:  # prelude
        pass
    while size_bytes := stream.read(4):
        header = _read_bson(stream, size_bytes)
        if header is None:
            raise ArchiveError("terminator where a namespace header was expected")
        collection = bson.decode(header)["collection"]
        while (doc := _read_bson(stream, stream.read(4))) is not None:
            yield collection, doc


def to_record(collection: str, raw: bytes) -> dict:
    """Project one Jira issue document onto the fields this project uses."""
    doc = bson.decode(raw, codec_options=_RAW)
    fields = doc.get("fields") or {}
    issuetype = fields.get("issuetype") or {}
    return {
        "tracker": collection,
        "id": doc.get("id"),
        "key": doc.get("key"),
        "project": (fields.get("project") or {}).get("key"),
        "issuetype_id": issuetype.get("id"),
        "issuetype": issuetype.get("name"),
        "status": (fields.get("status") or {}).get("name"),
        "created": fields.get("created"),
        "summary": fields.get("summary"),
        "description": fields.get("description"),
        "environment": fields.get("environment"),
        "versions": [v.get("name") for v in fields.get("versions") or []],
    }


def extract(zip_path: Path, out_path: Path) -> Counter:
    """Write one JSON line per issue to gzipped JSONL; return counts per tracker."""
    counts: Counter = Counter()
    with (
        zipfile.ZipFile(zip_path) as zf,
        zf.open(DUMP_PATH) as member,
        gzip.GzipFile(fileobj=member) as gz,
        gzip.open(out_path, "wt", encoding="utf-8") as out,
    ):
        for collection, raw in iter_documents(io.BufferedReader(gz, 1 << 20)):
            out.write(json.dumps(to_record(collection, raw), ensure_ascii=False) + "\n")
            counts[collection] += 1
    return counts


def main(argv: list[str]) -> None:
    zip_path, out_path = map(Path, argv)
    start = time.perf_counter()
    counts = extract(zip_path, out_path)
    for tracker, n in sorted(counts.items()):
        print(f"{tracker}\t{n}")
    print(f"TOTAL\t{counts.total()}\t({time.perf_counter() - start:.0f} s)")


if __name__ == "__main__":
    main(sys.argv[1:])
