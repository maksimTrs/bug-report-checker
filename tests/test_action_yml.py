import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
FILES = [ROOT / "action.yml", ROOT / "docs" / "example-workflow.yml"]


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_parses_as_a_mapping(path):
    assert isinstance(yaml.safe_load(path.read_text("utf-8")), dict)


def test_actions_are_pinned_to_a_commit():
    steps = yaml.safe_load((ROOT / "action.yml").read_text("utf-8"))["runs"]["steps"]
    uses = [s["uses"] for s in steps if "uses" in s]
    assert uses
    for ref in uses:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", ref), ref
