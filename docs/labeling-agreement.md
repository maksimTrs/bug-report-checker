# Labeling agreement

Per-check agreement of the teacher's labels with a reference set: `python -m bug_report_checker.labeling.agreement <reference.jsonl> <labels.jsonl>`. Labels are skewed (`actual` is "yes" in most reports), so the minority class is reported separately: always answering the majority would score high on the first column and zero on the last.

## Rubric check: Sonnet vs gold 20

Gold: `labeling/gold_20.jsonl` — 20 public reports chosen so every check has both classes, labelled by two independent model annotators against `labeling/rubric.md` (135/140 agreement), disagreements adjudicated. Teacher: `claude-sonnet-5-5` with `labeling/prompt.md` + `labeling/rubric.md`. Threshold: 17/20 per check.

| Check | Agreement | Minority class | Minority agreement |
|---|---|---|---|
| summary_what | 19/20 | no (7) | 6/7 |
| summary_where | 19/20 | no (2) | 2/2 |
| summary_when | 19/20 | no (9) | 9/9 |
| steps | 18/20 | no (9) | 8/9 |
| expected | 19/20 | no (5) | 5/5 |
| actual | 20/20 | no (4) | 4/4 |
| build_version | 19/20 | yes (5) | 5/5 |

The first run failed `summary_where` (16/20) and `expected` (16/20); the rubric was clarified (objects inside the product count as "where"; a crash, a hang or a working comparison states the expected result) and the run repeated. Since the rubric was tuned on these 20 reports, the agreement above is optimistic; the Sonnet ↔ Opus check on the 100 eval reports is the independent one.
