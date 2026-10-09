# Results

Fine-tuned Laya (`typed-decisions` checkpoint, 7 `noul` questions) on the frozen eval set: 100 public bug reports from projects that never appear in train, labelled by Opus with disagreements adjudicated ([labeling-agreement.md](labeling-agreement.md)).

## Setup

- **Two training runs.** Run 1: 300 reports, hard targets. It learned each check's prior and missed the rare "missing" cases (expected, actual), and was overconfident (mean confidence 0.94–0.99). Run 2: 544 reports, topped up with public reports that lack an expected or actual result, soft targets (0.95 / 0.05).
- **Selection without eval.** The runs were compared on a separate dev set (122 public reports, not in train, not from eval projects) by recall of "missing" on the four blockers and ECE. Run 2 won; eval was then scored once, on run 2. Run 1 had been scored on eval before that rule was set — its weak checks are what motivated run 2 — and is shown for reference.
- **Metrics.** "Missing" is the positive class: the bot exists to say what a report lacks, and labels lean towards "present", so plain accuracy flatters a model that always says yes. That baseline is in every table. Intervals are 95% Wilson; with 100 reports an accuracy near 80% is ±8 points, and recall on a check with 13–15 missing cases is far wider.

## Blockers at a glance

Recall of "missing" at the 0.5 cut (95% CI):

| Check | Missing in eval | Base Laya | Run 2 | Precision, run 2 | ECE, run 2 |
|---|---:|---:|---:|---:|---:|
| steps | 56 | 25% | 98% (91–100) | 85% | 0.096 |
| build_version | 76 | 29% | 87% (77–93) | 90% | 0.075 |
| expected | 15 | 27% | 47% (25–70) | 64% | 0.090 |
| actual | 13 | 46% | 38% (18–64) | 100% | 0.103 |

- **Steps and build version** are where the model earns its place: it finds nearly every report without steps or a version, and says "missing" wrongly on few complete ones.
- **Expected and actual** remain weak. Eval has few such reports (15 and 13), so the intervals are wide, but dev (75% and 93%) overstates them: most of dev's reports without an actual result were mined for that purpose and read as feature requests filed as bugs, which is the easy case. Eval's were not selected that way.
- **Calibration** improved from run 1 everywhere except `actual` (0.101 → 0.103): ECE 0.06–0.10, mean confidence 0.83–0.86.

## What the bot would say

Below a confidence of 0.824 (fitted by laya on the calibration slice for a 10% error target) the bot answers "not sure" instead of "present" or "missing".

| Check | Coverage | Accuracy decided | Missing → missing / not sure / present | Present → missing |
|---|---|---|---|---|
| summary_what | 96% | 82% | 11 / 3 / 16 of 30 | 1 of 70 |
| summary_where | 93% | 83% | 1 / 3 / 16 of 20 | 0 of 80 |
| summary_when | 88% | 85% | 31 / 8 / 9 of 48 | 4 of 52 |
| steps | 90% | 92% | 53 / 2 / 1 of 56 | 6 of 44 |
| expected | 86% | 94% | 5 / 7 / 3 of 15 | 2 of 85 |
| actual | 97% | 94% | 4 / 3 / 6 of 13 | 0 of 87 |
| build_version | 84% | 88% | 61 / 8 / 7 of 76 | 3 of 24 |

- Wrong "missing" on a complete report — the costly error, since it nags an author who did nothing wrong — stays at 0–6 per check; steps is highest (6 of 44).
- The weak checks lean on "not sure": for `expected`, 7 of 15 missing cases land there rather than as a wrong "present".
- `actual` is the bot's main blind spot: 6 of 13 reports without an actual result are confidently called complete.

## Per check

Every check, against always answering "yes" and the base model. Summary checks (what / where / when) are soft hints, not blockers.

#### summary_what

| Model | Accuracy (95% CI) | Recall missing (95% CI) | Precision missing | Confidence | ECE |
|---|---|---|---|---|---|
| always yes | 70% (60%–78%) | 0/30 = 0% (0%–11%) | — | 1.00 | 0.300 |
| base | 76% (67%–83%) | 14/30 = 47% (30%–64%) | 64% | 0.61 | 0.148 |
| run1 | 81% (72%–87%) | 11/30 = 37% (22%–54%) | 100% | 0.98 | 0.171 |
| run2 | 81% (72%–87%) | 12/30 = 40% (25%–58%) | 92% | 0.85 | 0.062 |

#### summary_where

| Model | Accuracy (95% CI) | Recall missing (95% CI) | Precision missing | Confidence | ECE |
|---|---|---|---|---|---|
| always yes | 80% (71%–87%) | 0/20 = 0% (0%–16%) | — | 1.00 | 0.200 |
| base | 70% (60%–78%) | 5/20 = 25% (11%–47%) | 25% | 0.61 | 0.112 |
| run1 | 81% (72%–87%) | 1/20 = 5% (1%–24%) | 100% | 0.99 | 0.187 |
| run2 | 82% (73%–88%) | 2/20 = 10% (3%–30%) | 100% | 0.85 | 0.073 |

#### summary_when

| Model | Accuracy (95% CI) | Recall missing (95% CI) | Precision missing | Confidence | ECE |
|---|---|---|---|---|---|
| always yes | 52% (42%–62%) | 0/48 = 0% (0%–7%) | — | 1.00 | 0.480 |
| base | 56% (46%–65%) | 9/48 = 19% (10%–32%) | 64% | 0.63 | 0.116 |
| run1 | 70% (60%–78%) | 39/48 = 81% (68%–90%) | 65% | 0.94 | 0.244 |
| run2 | 79% (70%–86%) | 34/48 = 71% (57%–82%) | 83% | 0.85 | 0.098 |

#### steps

| Model | Accuracy (95% CI) | Recall missing (95% CI) | Precision missing | Confidence | ECE |
|---|---|---|---|---|---|
| always yes | 44% (35%–54%) | 0/56 = 0% (0%–6%) | — | 1.00 | 0.560 |
| base | 56% (46%–65%) | 14/56 = 25% (16%–38%) | 88% | 0.62 | 0.094 |
| run1 | 80% (71%–87%) | 56/56 = 100% (94%–100%) | 74% | 0.98 | 0.187 |
| run2 | 89% (81%–94%) | 55/56 = 98% (91%–100%) | 85% | 0.84 | 0.096 |

#### expected

| Model | Accuracy (95% CI) | Recall missing (95% CI) | Precision missing | Confidence | ECE |
|---|---|---|---|---|---|
| always yes | 85% (77%–91%) | 0/15 = 0% (0%–20%) | — | 1.00 | 0.150 |
| base | 76% (67%–83%) | 4/15 = 27% (11%–52%) | 24% | 0.62 | 0.184 |
| run1 | 87% (79%–92%) | 5/15 = 33% (15%–58%) | 62% | 0.98 | 0.118 |
| run2 | 88% (80%–93%) | 7/15 = 47% (25%–70%) | 64% | 0.84 | 0.090 |

#### actual

| Model | Accuracy (95% CI) | Recall missing (95% CI) | Precision missing | Confidence | ECE |
|---|---|---|---|---|---|
| always yes | 87% (79%–92%) | 0/13 = 0% (0%–23%) | — | 1.00 | 0.130 |
| base | 83% (74%–89%) | 6/13 = 46% (23%–71%) | 38% | 0.63 | 0.253 |
| run1 | 89% (81%–94%) | 2/13 = 15% (4%–42%) | 100% | 0.99 | 0.101 |
| run2 | 92% (85%–96%) | 5/13 = 38% (18%–64%) | 100% | 0.86 | 0.103 |

#### build_version

| Model | Accuracy (95% CI) | Recall missing (95% CI) | Precision missing | Confidence | ECE |
|---|---|---|---|---|---|
| always yes | 24% (17%–33%) | 0/76 = 0% (0%–5%) | — | 1.00 | 0.760 |
| base | 46% (37%–56%) | 22/76 = 29% (20%–40%) | 100% | 0.61 | 0.179 |
| run1 | 79% (70%–86%) | 64/76 = 84% (74%–91%) | 88% | 0.95 | 0.157 |
| run2 | 83% (74%–89%) | 66/76 = 87% (77%–93%) | 90% | 0.83 | 0.075 |

## Style eval

30 synthetic reports for a fictional product, written in a team's own bug template (headed sections, build line, links and tables, three long spec-like reports of 13–16k characters scanned in windows). They were written by fresh agents that never saw the training texts, and labelled by Sonnet alone, with no second teacher or adjudication. Run 2 only, scored after selection; aggregates only, since the texts carry the template.

Recall of "missing" at the 0.5 cut (95% CI):

| Check | Missing | Base Laya | Run 2 | Precision, run 2 | Accuracy, run 2 | ECE, run 2 |
|---|---:|---:|---:|---:|---:|---:|
| build_version | 15 | 13% | 100% (80–100) | 94% | 97% | 0.167 |
| steps | 8 | 12% | 62% (31–86) | 83% | 87% | 0.110 |
| expected | 3 | 0% | 0% (0–56) | — | 90% | 0.046 |
| actual | 0 | — | — | — | 100% | 0.135 |
| summary_what | 10 | 20% | 30% (11–60) | 100% | 77% | 0.137 |
| summary_where | 0 | — | — | — | 100% | 0.137 |
| summary_when | 15 | 0% | 53% (30–75) | 80% | 70% | 0.162 |

- **Not tested here: `actual` and `expected`.** The set has no report without an actual result and three without an expected one, so it says nothing about the two weak checks; their accuracy above is the "always yes" share.
- **Build version carries over to the template**: every report without a build is found, one complete report is flagged.
- **Steps drop from 98% on eval to 62%**, and all three misses are the long spec-like reports. No report that long was in train; the model reads them in windows and calls steps present.
- **Expected stated as a question** ("should it …?") is read as an expected result in all three cases.
- At the 0.824 threshold the bot decides 83–100% of answers per check. The two false "missing" on blockers (one steps, one build) fall below it and become "not sure", so no present blocker part is flagged (0 of 94).
