"""Select bug reports using the dataset authors' issue-type mapping.

The authors mapped every issue type of every tracker to a theme and a code
(`jira_issuetype_thematic_analysis.json`, taken from `0. DataDefinition/` of the
Zenodo archive). Bugs are the types coded "Bug Report":
Bug, Defect and their per-tracker analogues. Types missing from the mapping are skipped.

Usage: python -m bug_report_checker.dataset.select_bugs \
    <issues.jsonl.gz> <mapping.json> <bugs.jsonl.gz>
"""

import gzip
import json
import sys
from collections import Counter
from pathlib import Path

BUG_CODE = "Bug Report"


def load_bug_types(mapping_path: Path) -> dict[str, set[str]]:
    """Issue type names coded as bug reports, per tracker."""
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    bug_types = {
        tracker: {name for name, m in types.items() if m["code"] == BUG_CODE}
        for tracker, types in mapping.items()
    }
    return {tracker: names for tracker, names in bug_types.items() if names}


def select_bugs(
    issues_path: Path, mapping_path: Path, out_path: Path
) -> tuple[Counter, Counter]:
    """Copy bugs to `out_path`; return per-tracker counts: bugs, with description."""
    bug_types = load_bug_types(mapping_path)
    bugs: Counter = Counter()
    with_description: Counter = Counter()
    with (
        gzip.open(issues_path, "rt", encoding="utf-8") as src,
        gzip.open(out_path, "wt", encoding="utf-8") as out,
    ):
        for line in src:
            record = json.loads(line)
            tracker = record["tracker"]
            if record["issuetype"] not in bug_types.get(tracker, ()):
                continue
            out.write(line)
            bugs[tracker] += 1
            if (record["description"] or "").strip():
                with_description[tracker] += 1
    return bugs, with_description


def main(argv: list[str]) -> None:
    bugs, with_description = select_bugs(*map(Path, argv))
    print("tracker\tbugs\twith_description")
    for tracker in sorted(bugs):
        print(f"{tracker}\t{bugs[tracker]}\t{with_description[tracker]}")
    print(f"TOTAL\t{bugs.total()}\t{with_description.total()}")


if __name__ == "__main__":
    main(sys.argv[1:])
