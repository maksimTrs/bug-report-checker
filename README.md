# bug-report-checker

GitHub Action that checks whether a newly filed bug report is complete — steps to reproduce, expected and actual result, build version — and comments with what is missing.

Decisions are made by a fine-tuned [Laya](https://github.com/NandhaKishorM/laya) model running on free CPU runners.

> Work in progress.

## Data attribution

Trained on a public dataset and synthetic examples.

Data: The Public Jira Dataset — Montgomery L., Lüders C., Maalej W. *An Alternative Issue Tracking Dataset of Public Jira Repositories.* MSR 2022. DOI: [10.1145/3524842.3528486](https://doi.org/10.1145/3524842.3528486). Dataset: https://doi.org/10.5281/zenodo.5882881. License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
