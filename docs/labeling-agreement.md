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

## Sonnet vs Opus on the 100 eval reports

Both teachers labelled `data/eval.jsonl` with the same prompt and rubric, independently: `claude-sonnet-5-5` (all 430 reports) and `claude-opus-5-5` (eval only). Reference column: Opus. Threshold: 85% per check; below it the rubric would be revised and the check relabelled.

| Check | Agreement | Minority class (Opus) | Minority agreement |
|---|---|---|---|
| summary_what | 85/100 | no (30) | 16/30 |
| summary_where | 93/100 | no (20) | 13/20 |
| summary_when | 93/100 | no (48) | 44/48 |
| steps | 94/100 | yes (45) | 41/45 |
| expected | 90/100 | no (18) | 14/18 |
| actual | 95/100 | no (11) | 8/11 |
| build_version | 96/100 | yes (24) | 22/24 |

- Every check passes; no relabelling. The blockers (steps, expected, actual, build_version) agree on 90–96 reports.
- The weak spot is `summary_what`: the teachers agree on only half of the titles Opus calls defect-free (16/30). It is a hint, not a blocker, and can be switched off without touching completeness.
- `expected` and `actual` disagree mostly on the minority class (4 of 18, 3 of 11): the student's recall on missing parts will be bounded by this teacher noise.
- Disagreements are reviewed by hand before the eval set is frozen (T2.8).

## Label balance (Sonnet, share of "yes")

| Check | Train (300) | Eval (100) | Style-eval (30) |
|---|---:|---:|---:|
| summary_what | 85% | 83% | 67% |
| summary_where | 91% | 87% | 100% |
| summary_when | 47% | 53% | 50% |
| steps | 50% | 43% | 73% |
| expected | 82% | 80% | 90% |
| actual | 93% | 90% | 100% |
| build_version | 26% | 24% | 50% |

## Frozen eval set

`eval/eval.jsonl` — the 100 eval reports with final labels, not to be changed. Labels: Opus, except the 25 blocker labels (21 reports) where Sonnet and Opus disagreed — each was decided against the rubric; 19 kept Opus, 6 took Sonnet. Hint disagreements (summary checks) keep Opus without review.

Agreement of each teacher with the final labels:

| Check | Opus | Sonnet |
|---|---:|---:|
| steps | 99/100 | 95/100 |
| expected | 97/100 | 93/100 |
| actual | 98/100 | 97/100 |
| build_version | 100/100 | 96/100 |

## Eval v2

Eval v1 was read while planning run 3 (the run 2 misses on it shaped a draft top-up), so it now serves as dev and a new eval was built: `eval/eval_v2.jsonl`, 170 reports from 115 projects that no other set uses.

- **Random core, 100 reports** (`"core": true`), drawn by the same scheme as eval v1 and set aside before any label was seen. Accuracy and precision are read here.
- **70 added reports** where Sonnet found the actual or the expected result missing, so the two weak checks have enough cases for recall: 41 reports without an actual result, 53 without an expected one (10 and 12 of them in the core). Mojang, IntelDAOS and SecondLife have no unused project left, so they are absent.
- **Labels:** Opus on all 170, the 63 blocker disagreements with Sonnet (59 reports) decided against the rubric: 59 kept Opus, 4 took Sonnet (`actual`: an improvement or a "should" with no observed result). E-mail addresses in five reports are replaced with `[email]`.

Sonnet vs final labels on the random core (on all 170 the added part inflates disagreement, since it was picked by Sonnet's answers):

| Check | Agreement | Minority class | Minority agreement |
|---|---|---|---|
| summary_what | 83/100 | no (29) | 13/29 |
| summary_where | 94/100 | no (10) | 7/10 |
| summary_when | 87/100 | yes (42) | 36/42 |
| steps | 92/100 | yes (47) | 41/47 |
| expected | 90/100 | no (12) | 9/12 |
| actual | 96/100 | no (10) | 6/10 |
| build_version | 100/100 | yes (18) | 18/18 |

- Blockers agree on 90–100 of 100, above the 85% bar. `summary_what` (83) is again the weakest and stays a hint.
- On the added reports Sonnet calls the expected result missing far more often than Opus: 32 of the 36 `expected` disagreements are Sonnet "no", Opus "yes" — mostly crashes, errors and negations whose correct behaviour is plain, which the rubric counts as stated. Train labels come from Sonnet, so they carry the same lean.
