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

A bug is an issue whose type the dataset authors coded as **Bug Report** in `jira_issuetype_thematic_analysis.json` (theme Maintenance), matched per tracker by type name: `python -m bug_report_checker.dataset.select_bugs`. Output: `data/raw/bugs.jsonl.gz` (507 MB).

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
