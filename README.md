# bug-report-checker

GitHub Action that checks whether a newly filed bug report is complete — steps to reproduce, expected and actual result, build version — and comments with what is missing.

Decisions are made by a fine-tuned [Laya](https://github.com/NandhaKishorM/laya) model running on free CPU runners: [ippo123/bug-report-checker](https://huggingface.co/ippo123/bug-report-checker).

Strict mode — `strict: true` in `.github/bug-checker.yml` (off by default): steps, expected and actual result count only when the description itself states them — at least two steps or a command that reproduces the bug, an expected result in words (not just a negation of the symptom), an actual result that is concrete rather than "doesn't work". A clear title with one vague line is no longer a complete report.

> Work in progress.

## Data attribution

Trained on a public dataset and synthetic examples.

Data: The Public Jira Dataset — Montgomery L., Lüders C., Maalej W. *An Alternative Issue Tracking Dataset of Public Jira Repositories.* MSR 2022. DOI: [10.1145/3524842.3528486](https://doi.org/10.1145/3524842.3528486). Dataset: https://doi.org/10.5281/zenodo.5882881. License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

`eval/eval.jsonl`, `eval/eval_v2.jsonl`, `eval/strict_gold.jsonl` (its `public` records) and `labeling/gold_20.jsonl` contain bug reports from this dataset, changed: preprocessed (links reduced to hosts, images to `[image]`, code cut to a few lines) and e-mail addresses redacted. The completeness labels are ours.
