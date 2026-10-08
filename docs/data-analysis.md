# Data analysis

## Source

The Public Jira Dataset, Zenodo record [15719919](https://zenodo.org/records/15719919) (version of 2025-06-23, anonymised: people replaced with UUIDs), file `2025-06-23 ThePublicJiraDataset.zip`, 5 813 135 238 bytes, MD5 `02f85309d966092ea130ca0797aea795`. License: CC BY 4.0.

The dump is a gzipped `mongodump --archive` (MongoDB 7.0.14, one collection per Jira repository). Restored, it takes ~60 GB, mostly change history and comments. Instead of restoring it, `python -m bug_report_checker.dataset.jira_dump` streams the archive out of the zip and keeps a few fields per issue: tracker, id, key, project, issue type, status, created, summary, description, environment, affected versions.

Output: `data/raw/issues.jsonl.gz` (733 MB), extracted in 21 minutes on a desktop CPU.

## Integrity check

Issues per repository match Table 1 of Montgomery et al., MSR 2022, exactly:

| Repository | Table 1 | Extracted |
|---|---:|---:|
| Apache | 1,014,926 | 1,014,926 |
| Hyperledger | 28,146 | 28,146 |
| IntelDAOS | 9,474 | 9,474 |
| JFrog | 15,535 | 15,535 |
| Jira | 274,545 | 274,545 |
| JiraEcosystem | 41,866 | 41,866 |
| MariaDB | 31,229 | 31,229 |
| Mindville | 2,134 | 2,134 |
| Mojang | 420,819 | 420,819 |
| MongoDB | 137,172 | 137,172 |
| Qt | 148,579 | 148,579 |
| RedHat | 353,000 | 353,000 |
| Sakai | 50,550 | 50,550 |
| SecondLife | 1,867 | 1,867 |
| Sonatype | 87,284 | 87,284 |
| Spring | 69,156 | 69,156 |
| **Total** | **2,686,282** | **2,686,282** |

## Bug selection

A bug is an issue whose type the dataset authors coded as **Bug Report** in `jira_issuetype_thematic_analysis.json` (theme Maintenance), matched per tracker by type name: `python -m bug_report_checker.dataset.select_bugs` (the mapping file is copied from `0. DataDefinition/` of the archive to `data/raw/`). Output: `data/raw/bugs.jsonl.gz` (507 MB).

Types coded Bug Report, issues across all trackers: Bug 1,521,015 · Defect 1,280 · Public Security Vulnerability 98 · Story Defect 61 · Outage 43 · Incident 33 · Issue 4 · Atlassian Incident 4. The non-Bug/Defect types are under 0.02% and kept as the authors coded them.

Issue types absent from the mapping: 9,739 issues, almost all Sonatype "Publishing Support" (support requests, not bugs) — skipped.

| Tracker | Bugs | With non-empty description |
|---|---:|---:|
| Apache | 523,110 | 502,096 |
| Hyperledger | 7,622 | 7,284 |
| IntelDAOS | 3,616 | 3,518 |
| JFrog | 8,236 | 7,592 |
| Jira | 131,138 | 127,490 |
| JiraEcosystem | 20,414 | 18,000 |
| MariaDB | 22,800 | 22,580 |
| Mindville | 860 | 854 |
| Mojang | 420,819 | 413,910 |
| MongoDB | 48,122 | 44,656 |
| Qt | 106,804 | 105,809 |
| RedHat | 160,937 | 151,709 |
| Sakai | 33,216 | 33,195 |
| SecondLife | 1,231 | 1,231 |
| Sonatype | 6,495 | 6,418 |
| Spring | 27,118 | 26,068 |
| **Total** | **1,522,538** | **1,472,410** (96.7%) |

Mojang is a bug-only tracker (every issue is a Bug) and holds 28% of all bugs; Apache holds 34%. Sampling (T1.11) has to stratify by tracker so these two do not dominate.

## Length in Laya tokens

Bugs with a description, after preprocessing (`preprocess(..., jira=True)`), counted the way Laya counts the state: JSON of `{summary, description}`, tokenized without special tokens by the `laya-typed-decisions` tokenizer. Random 5% sample, seed 0: `python -m bug_report_checker.dataset.token_stats data/raw/bugs.jsonl.gz <checkpoint>/tokenizer/tokenizer.json 0.05`.

The state gets `max_len - question head - 1` tokens. For `laya-typed-decisions` (`max_len` 1024, `head_max_len` 256) the worst case is 767; 895 assumes a 128-token head.

| Tracker | Sample | Median | p90 | p99 | > 767 | > 895 |
|---|---:|---:|---:|---:|---:|---:|
| Apache | 25,134 | 157 | 540 | 2,475 | 5.8% | 4.4% |
| Hyperledger | 340 | 192 | 603 | 2,918 | 8.2% | 7.1% |
| IntelDAOS | 175 | 261 | 918 | 2,792 | 15.4% | 11.4% |
| JFrog | 420 | 187 | 587 | 3,380 | 6.7% | 5.0% |
| Jira | 6,189 | 155 | 418 | 1,345 | 2.8% | 1.8% |
| JiraEcosystem | 848 | 112 | 361 | 762 | 1.1% | 0.8% |
| MariaDB | 1,203 | 256 | 809 | 2,314 | 11.0% | 8.3% |
| Mindville | 47 | 148 | 335 | 419 | 0.0% | 0.0% |
| Mojang | 20,897 | 79 | 201 | 748 | 1.0% | 0.8% |
| MongoDB | 2,301 | 142 | 479 | 1,988 | 4.3% | 3.4% |
| Qt | 5,301 | 140 | 403 | 2,125 | 3.7% | 2.9% |
| RedHat | 7,656 | 144 | 482 | 1,776 | 4.0% | 3.1% |
| Sakai | 1,723 | 116 | 383 | 1,361 | 2.7% | 1.9% |
| SecondLife | 60 | 144 | 281 | 639 | 0.0% | 0.0% |
| Sonatype | 355 | 163 | 593 | 2,695 | 4.8% | 3.4% |
| Spring | 1,318 | 178 | 502 | 1,577 | 3.7% | 3.0% |
| **Total** | **73,967** | **123** | **424** | **1,810** | **3.7%** | **2.9%** |

96% of bugs fit one 1024-token sequence even with the largest question head; the 3–4% tail goes through `predict_long` (sliding windows). Mojang reports are the shortest (median 79), MariaDB and IntelDAOS the longest — sampling (T1.11) should keep length buckets, not only trackers.

## Manual review of 50 bugs

50 bugs with a description, reservoir-sampled over the whole file (`random.Random(10)`), read after preprocessing. Trackers: Mojang 16, Apache 11, Qt 7, RedHat 6, Jira 6, Spring 2, IntelDAOS 1, Sakai 1 (Jira counts BCLOUD/JRACLOUD/CONFSERVER/SRCTREEWIN).

"Explicit" means a section or a list; "in prose" means the content is there but has to be inferred from free text.

| Part of the report | Explicit | In prose only | Missing |
|---|---:|---:|---:|
| Steps to reproduce | 9 (18%) | 27 (54%) | 14 (28%) |
| Expected result | 10 (20%) | 16 (32%) — only as a negation, "X does not work" | 24 (48%) |
| Actual result | 46 (92%) | — | 4 (8%) |
| Version in summary or description | 9 (18%) | — | 41 (82%) |

- **Free form dominates.** Only 4 of 50 (8%) use headed sections (Steps / Expected / Actual); one of them is the Mojang template left unfilled, placeholders only — a clean "missing everything" case.
- **Version lives in the Jira field, not the text.** `versions` (Affects Version) is set for 39 of 50, but the text names a version in 9. The model sees only summary and description, so public bugs give few positive version examples.
- **Actual is almost always there** (92%): a bug report is, first of all, a description of what went wrong. Most reports with no explicit steps still describe the scenario in prose.
- **Summary.** Most name the defect and the place. Weak ones: a bare noun ("Oven", "Flash, PDF and plugins"), a plea ("help!!!!"), a question, or a task ("Mirror pull requests…", "Release Steps 5.4.6"). A condition or trigger ("when…", "after…", "on Windows") appears in about a third.
- **Not every Bug is a bug:** 2 of 50 are a question / feature request and a release checklist. Expected noise for the teacher to label as incomplete.
- **Attachments:** one report with `[image]` in 50; screenshots in the public data are rare.

Rare parts to top up in sampling (T1.11) and synthetic data (T1.12): explicit steps, explicit expected result, version or build number in the text, headed templates (filled, partially filled, empty), screenshot-only results.

Preprocessing gaps found on the way (1% sample, share of descriptions): HTML entities such as `&#x27;` — 1.2% (Apache, Jira Cloud); Jira forced line break `\` — 0.5%; unified diffs (`@@ -1,7 +1,7 @@`) are not shortened like code blocks — 0.2%.
