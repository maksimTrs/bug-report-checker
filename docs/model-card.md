---
license: apache-2.0
language:
  - en
base_model: convaiinnovations/laya
tags:
  - laya
  - bug-reports
  - text-classification
---

# bug-report-checker

Checks whether a bug report is complete. Given a report's summary and description, it answers seven yes / no questions, each with a probability. Fine-tuned from the `typed-decisions` checkpoint of [Laya](https://huggingface.co/convaiinnovations/laya); runs on a CPU.

| Key | Question |
|---|---|
| `steps` | Does the description give steps to reproduce? |
| `expected` | Does the report state the expected result? |
| `actual` | Does the report state the actual result? |
| `build_version` | Does the report name the product version or build? |
| `summary_what` | Does the summary say what is wrong? |
| `summary_where` | Does the summary say where it happens? |
| `summary_when` | Does the summary say when it happens? |

## Usage

```python
import json

import laya
from huggingface_hub import hf_hub_download

REPO = "ippo123/bug-report-checker"
questions = json.load(open(hf_hub_download(REPO, "questions.json"), encoding="utf-8"))
agent = laya.load(REPO, device="cpu")

report = {
    "summary": "Export to CSV crashes on save",
    "description": "1. Open a report\n2. Click Export\nThe app closes. Version 4.18.2",
}
answers = agent.predict_long(report, questions)["answers"]
p_present = {check: a["noul"] for check, a in answers.items()}
```

Requires `laya==0.4.0`.

## Data

Trained on a public dataset and synthetic examples. Data: The Public Jira Dataset — Montgomery L., Lüders C., Maalej W. *An Alternative Issue Tracking Dataset of Public Jira Repositories.* MSR 2022. DOI: [10.1145/3524842.3528486](https://doi.org/10.1145/3524842.3528486). Dataset: https://doi.org/10.5281/zenodo.5882881. License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
