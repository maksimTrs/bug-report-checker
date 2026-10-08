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
