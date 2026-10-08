import gzip
import json

from bug_report_checker.dataset.select_bugs import load_bug_types, select_bugs

MAPPING = {
    "Apache": {
        "Bug": {"theme": "Maintenance", "code": "Bug Report"},
        "Documentation": {"theme": "Maintenance", "code": "Documentation"},
        "Task": {"theme": "Development", "code": "Task"},
    },
    "RedHat": {"Defect": {"theme": "Maintenance", "code": "Bug Report"}},
}


def _mapping(tmp_path):
    path = tmp_path / "mapping.json"
    path.write_text(json.dumps(MAPPING), encoding="utf-8")
    return path


def _issues(tmp_path, records):
    path = tmp_path / "issues.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in records)
    return path


def test_load_bug_types_keeps_only_bug_report_code(tmp_path):
    assert load_bug_types(_mapping(tmp_path)) == {
        "Apache": {"Bug"},
        "RedHat": {"Defect"},
    }


def test_select_bugs_filters_by_tracker_specific_type_and_counts(tmp_path):
    records = [
        {"tracker": "Apache", "key": "A-1", "issuetype": "Bug", "description": "x"},
        {"tracker": "Apache", "key": "A-2", "issuetype": "Bug", "description": " "},
        {"tracker": "Apache", "key": "A-3", "issuetype": "Task", "description": "x"},
        {"tracker": "Apache", "key": "A-4", "issuetype": "Defect", "description": "x"},
        {"tracker": "RedHat", "key": "R-1", "issuetype": "Defect", "description": None},
        {"tracker": "Unknown", "key": "U-1", "issuetype": "Bug", "description": "x"},
    ]
    out = tmp_path / "bugs.jsonl.gz"

    bugs, with_description = select_bugs(
        _issues(tmp_path, records), _mapping(tmp_path), out
    )

    assert bugs == {"Apache": 2, "RedHat": 1}
    assert with_description == {"Apache": 1}
    with gzip.open(out, "rt", encoding="utf-8") as fh:
        assert [json.loads(line)["key"] for line in fh] == ["A-1", "A-2", "R-1"]
