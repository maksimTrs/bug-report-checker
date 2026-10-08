import json

from bug_report_checker.labeling.teacher import batch_input, parse_answer, system_prompt


def test_system_prompt_is_prompt_then_rubric(tmp_path):
    (tmp_path / "prompt.md").write_text("PROMPT\n", encoding="utf-8")
    (tmp_path / "rubric.md").write_text("RUBRIC\n", encoding="utf-8")

    assert system_prompt(tmp_path) == "PROMPT\n\nRUBRIC\n"


def test_batch_input_sends_only_id_and_text():
    rows = [
        {
            "id": "Apache:X-1",
            "source": "public",
            "tracker": "Apache",
            "project": "X",
            "summary": "Crash on save",
            "description": "Steps: …",
        }
    ]

    lines = batch_input(rows).splitlines()

    assert [json.loads(line) for line in lines] == [
        {"id": "Apache:X-1", "summary": "Crash on save", "description": "Steps: …"}
    ]


def test_batch_input_keeps_non_ascii():
    text = batch_input([{"id": "a", "summary": "Ошибка", "description": "é"}])

    assert "Ошибка" in text


def test_parse_answer_reads_one_object_per_line():
    answer = '{"id": "a", "steps": true}\n\n{"id": "b", "steps": false}\n'

    assert parse_answer(answer) == [
        {"id": "a", "steps": True},
        {"id": "b", "steps": False},
    ]
