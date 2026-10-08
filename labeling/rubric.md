# Bug report rubric (v1)

The teacher model answers seven yes / no questions about each bug report. The labels train a small model that tells a reporter what their bug report is missing.

**Input:** the bug report after preprocessing — `summary` and `description`, the same text the trained model sees. Preprocessing has already:

- removed leading `[Tag]` prefixes from the summary, HTML comments and struck-through text;
- replaced images, videos and attachments with `[image]`;
- replaced every URL with `[link: host]` (a labelled link becomes `label [link: host]`);
- cut code blocks and stack traces to their first lines, followed by `[… truncated]`.

## Checks

| # | Key | Question | Level |
|---|---|---|---|
| 1 | `summary_what` | Does the summary say **what** is wrong? | hint |
| 2 | `summary_where` | Does the summary say **where** it happens? | hint |
| 3 | `summary_when` | Does the summary say **when** it happens (action or condition)? | hint |
| 4 | `steps` | Does the description give steps to reproduce? | blocker |
| 5 | `expected` | Does the report state the expected result? | blocker |
| 6 | `actual` | Does the report state the actual result? | blocker |
| 7 | `build_version` | Does the report name the product version or build? | blocker |

A **blocker** makes the report incomplete; a **hint** is a soft suggestion. The level does not change how a check is labelled.

## General rules

1. **Meaning, not headings.** Content counts wherever it is: under any heading, in a list, in prose. A heading with nothing under it, or with only `TBD`, `-`, `N/A`, `?`, counts as missing.
2. **Where to look.** Checks 1–3: the summary only. Steps: the description only — a trigger in the summary is already credited to `summary_when`. Expected, actual and version: the whole report, summary included.
3. **Present is not the same as good.** Label whether the part is there, not how well it is written. Short, clumsy or non-native text still counts.
4. **Not every "bug" is a bug.** Questions, feature requests and checklists filed as bugs are labelled by the same definitions; most checks usually come out "no".
5. **When in doubt, ask: could a developer act on it without asking back?** If they would have to ask "what exactly?", the answer is "no".

Not labelled here, decided by code: the test environment (stand / production) and the "describe the result in words, not only a screenshot" hint.

---

## 1. `summary_what` — what is wrong

**Yes:** the summary names the faulty behaviour — a crash, an error, a wrong or missing value, a hang, a slowdown, an element that does not appear. An exception name counts. The grammatical form does not matter: "Fix crash when …" still names the defect.

**No:** a bare noun or area ("Tracking page"), a task with no symptom ("Increase pickup slot timeout", "Add retry to label printing"), a plea or a question ("Help!!!", "Is this expected?"), a failure too vague to act on ("does not work", "is broken", "issue with …").

| Summary | Label | Why |
|---|---|---|
| `Fix label printing crash for parcels over 30 kg` | yes | Task form, but the defect (a crash) is named. Form is a style matter, not this check. |
| `Courier app: route map` | no | An area and an object, nothing is said to be wrong. |
| `QR code is missing on return labels` | yes | "Missing" is the defect. Compare `Return label QR code` — no. |

## 2. `summary_where` — where it happens

**Yes:** the summary names a place in the product — a screen, page, dialog, feature, component, endpoint, background job, module or class. A leading `Area:` word counts when it names a place ("Checkout: …"); a leading word that names the defect ("Crash: …", "Regression: …") does not.

**No:** only the product as a whole ("the app", "Parcelwise", "the system"), or no place at all.

| Summary | Label | Why |
|---|---|---|
| `Parcelwise app freezes after login` | no | The whole product is not a place. (`summary_when` is yes.) |
| `Crash: NullPointerException in ManifestExporter.write` | yes | The class and method are the place; `Crash:` is the what, not the where. |
| `Wrong VAT on invoice PDF` | yes | The invoice PDF is the place. |

## 3. `summary_when` — action or condition

**Yes:** the summary names what triggers the problem — an action ("after changing the address", "on save"), a moment ("on startup", "after upgrade"), or a condition ("for parcels over 30 kg", "with an empty cart", "on Android").

**No:** the symptom alone, a frequency that is not a condition ("sometimes", "intermittently", "randomly"), or a clause that qualifies a requested task rather than triggering the problem ("Archive finished routes when the shift is over").

| Summary | Label | Why |
|---|---|---|
| `Label printing fails for parcels over 30 kg` | yes | The weight is the condition. |
| `Courier app crashes intermittently` | no | "Intermittently" says how often, not when. |
| `Duplicate delivery notifications` | no | No trigger. |

## 4. `steps` — steps to reproduce

Looked for in the description only.

**Yes:** another person could try to reproduce the problem from the text:

- an ordered list of actions, under any heading or none ("Steps", "Case", "Scenario");
- prose that walks through concrete actions in order ("I booked a pickup, then changed the address…");
- a code snippet, test or command together with an instruction to run it — even if the code is `[… truncated]`.

**No:**

- no steps at all, or the summary repeated in other words;
- "unknown", "can't reproduce reliably", "steps not known" — even with an explanation of when it was seen;
- pre-conditions only: the setup is given, the action that triggers the problem is not;
- a stack trace or a code fragment with no word on how it is triggered;
- vague usage ("used the app for a while and it broke").

| Description (excerpt) | Label | Why |
|---|---|---|
| `Pre-conditions: courier account with two active routes.`<br>`Actual: route list is empty.` | no | Setup without the action. |
| `Steps: unknown, it happened twice during the night shift on the depot scanners.` | no | Unknown steps are missing steps, whatever the reason. |
| `Run the test below, it fails on the second assertion:`<br>`@Test void roundsParcelWeight() {`<br>`[… truncated]` | yes | A runnable reproduction with an instruction to run it. |

## 5. `expected` — expected result

**Yes:**

- the correct behaviour is stated, under any heading or in prose ("should", "expected", "instead of");
- the correct behaviour follows **unambiguously and concretely** from a negation: "the Print button does nothing" → it should print; "the app crashes on login" → it should log in;
- only `[image]` under an expected-result heading.

**No:**

- nothing about the correct behaviour;
- a vague negation that leaves the correct result open: "works incorrectly", "shows a wrong amount", "is broken";
- a request or a question instead of a result ("please investigate", "@lead, what should happen here?");
- a screenshot with no expected-result heading: it shows what happened, not what should;
- **an expected-result field that is present but empty — always "no"**, even if a negation elsewhere would imply the answer.

| Report (excerpt) | Label | Why |
|---|---|---|
| `Invoice shows the wrong VAT amount for Belgian addresses.` | no | Wrong, but the right amount is not given. |
| `Tapping "Print label" does nothing: no dialog, no error.` | yes | The correct behaviour (the label prints) is unambiguous. |
| `Expected:`<br>`Actual: the app closes when I tap Save.` | no | The expected field is empty. The rule for an empty field wins over the negation. |
| `Expected: not sure, @dispatch-lead should cancelled pickups stay on the list?` | no | A question, not a result. |

## 6. `actual` — actual result

**Yes:** the report says what actually happens — the symptom, the wrong value, the error message, the crash. Any of these counts on its own:

- a stack trace or an error log, even with no other text;
- only `[image]`, under an actual-result heading or, in a report without headings, with nothing but generic words ("see screenshot") — a screenshot of a bug shows what happened;
- the symptom stated in the summary only.

**No:** the report says only what should happen or what to do, the actual-result field is empty, or the "symptom" is too vague to name anything ("something is off", "doesn't work right").

| Report (excerpt) | Label | Why |
|---|---|---|
| A description that is only a stack trace: `java.lang.IllegalStateException: route already closed`<br>`at …`<br>`[… truncated]` | yes | The exception is the observed result. |
| `Actual: [image]` | yes | A screenshot counts; the text hint is added by code. |
| Summary `Pickup booking`, description `Please look at the booking flow, something is off.` | no | Nothing observable is described. |

## 7. `build_version` — product version or build

**Yes:** a concrete version number, build number or commit hash of the product where the bug was seen, anywhere in the summary or description: `Version: 4.18.2`, `build 5531`, `since upgrading to 3.2`, `on commit 9f2c1ab`.

**No:**

- no version, or an empty version field;
- a moving target with no number: "latest", "current prod", "master", "nightly", "3.x";
- only the version of something else: OS, browser, device, JDK, a third-party library;
- a version where it should be fixed ("should be fixed in 5.0"), not where it was seen;
- a link with no visible number (`Build: [link: ci.parcelwise.example]`).

| Report (excerpt) | Label | Why |
|---|---|---|
| `Version: Android 14, Pixel 7` | no | OS and device, not the product. |
| `Version: current prod` | no | Changes over time; the bug cannot be pinned to a build. |
| `Started after the depot scanner app was updated from 2.7.1 to 2.8.0.` | yes | 2.8.0 is the version where the bug was seen. |
