import json
from types import SimpleNamespace

from bug_report_checker.dataset.token_stats import state_tokens, summarize


class WhitespaceTokenizer:
    def encode_batch(self, texts, add_special_tokens=True):
        assert add_special_tokens is False
        return [SimpleNamespace(ids=text.split()) for text in texts]


def test_state_tokens_counts_serialized_preprocessed_state():
    records = [
        {"summary": "[UI] Save fails", "description": "Click *Save*\r\n\r\nh3. Logs"},
        {"summary": "Crash", "description": None},
    ]
    states = [
        {"summary": "Save fails", "description": "Click **Save**\n\n### Logs"},
        {"summary": "Crash", "description": ""},
    ]
    expected = [len(json.dumps(s, ensure_ascii=False).split()) for s in states]
    assert state_tokens(WhitespaceTokenizer(), records) == expected


def test_summarize_percentiles_and_share_over_room():
    stats = summarize(list(range(1, 101 + 1)), rooms=(91, 101))
    assert stats == {
        "n": 101,
        "median": 51,
        "p90": 91,
        "p99": 100,
        "over": {91: 10 / 101, 101: 0.0},
    }
