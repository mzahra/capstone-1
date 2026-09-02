# Delivery Plan

## What "AI Manager" means for this sprint

This capstone also serves as evidence for an AI Manager certification. The technical files in
this repo (the pipeline, the compliance docs, the ROI numbers) are what an AI Manager is
responsible for getting right. This file is the other half of that role: turning a business
problem into a scoped set of work, owning the sprint's delivery cadence, and being honest about
what shipped versus what did not, rather than only documenting the finished technology.

## User stories

| # | As a... | I want... | So that... | Status |
|---|---|---|---|---|
| 1 | Consultant | free text fields flagged for detected PII before a report reaches a client | I don't accidentally expose personal data | Done |
| 2 | Chleo (owner) | proof the pipeline works on more than one client's data shape, at real scale | I trust it won't break on the next new client, not just the demo dataset | Done, tested against 17.4 million real CFPB rows, not a small slice |
| 3 | Consultant | failed AI-generated KPI SQL to self-correct | I don't spend review time fixing basic AI mistakes by hand | Done, retries up to 5 times against the model itself |
| 4 | Chleo (owner) | the real ROI and risk of this tool in numbers | I can decide whether it is worth the investment | Done |
| 5 | Chleo (owner) | to know whether this tool is legally usable before real client data touches it | I don't create liability for my firm | Done |
| 6 | Future client | to know upfront that part of my onboarding is AI-assisted and human-reviewed | I can trust the report I receive | Addressed in `strategic_plan.md`'s stakeholder communication plan |
| 7 | Teaching evaluator | a working MVP I can actually try, not just documentation | the capstone claim is verifiable | Done, `mvp_documentation.md` |
| 8 | Teaching evaluator | a low-code POC alongside the production pipeline | I can see the same capability built a second, more accessible way | Deferred, see Definition of done below |
| 9 | Chleo (owner) | proof the pipeline can ingest a client's data even when it is not a clean flat table, genuinely nested JSON with an inconsistent schema | I know this isn't limited to whatever format one client happens to use | Done, Open Food Facts converted into 4 relational tables, real foreign keys confirmed between all of them |

## Definition of done

- [x] Pipeline runs end to end on all three datasets without crashing, verified with real runs,
      not just unit-level checks.
- [x] No raw PII appears in `outputs/*.json` or in any prompt sent to OpenAI, verified by
      printing the actual prompt text once against real CFPB narrative data.
- [x] `use_case_definition.md` written, with 2 or more measurable success criteria.
- [x] `roi_risk_assessment.md` written, with ROI at 12 and 36 months and a 6-or-more-risk matrix.
- [x] `compliance/eu_ai_act_compliance.md` and `compliance/gdpr_documentation.md` written.
- [x] `strategic_plan.md` written.
- [x] `mvp_documentation.md` written.
- [x] At least one genuinely semi-structured (not just messy-but-flat) dataset ingested and
      converted into relational tables, per `feedback/round1_decision.md`'s original commitment.
- [ ] No-code/low-code POC, workflow export, and demo recording. Deferred: the user chose to
      prioritize the production pipeline's scope over the POC this sprint. Still required for
      final submission, moved to day 4. Per the teacher's guidance, this can be built in plain
      Python, no n8n or other no-code tool required.
- [ ] Final presentation. Day 4.
- [x] Round 1 materials still present in the repo, nothing was removed, only extended.

## Acceptance criteria

**Story 1, PII flagging:**
Given a free text column containing a name, email, or phone number,
when the pipeline profiles that table,
then the column is flagged with entity-type counts, and any sample value shown to the AI or
saved to `outputs/profiling.json` has that PII redacted, not shown raw.
Verified: `order_reviews.review_comment_message` (Olist) and `Consumer complaint narrative`
(CFPB) both triggered this, redaction confirmed by inspecting the actual outbound prompt text.

**Story 2, generalization at scale:**
Given a client dataset structurally different from Olist, and far larger,
when the full pipeline runs against it,
then it completes without crashing or exhausting memory, and produces real KPI numbers computed
against the full dataset, not an estimate.
Verified: 17,456,743 CFPB rows loaded, profiled in about 90 seconds, and 5 of 5 KPIs computed
from the true full table.

**Story 3, KPI SQL self-correction:**
Given a KPI's generated SQL fails against the real schema,
when the pipeline retries it,
then the exact error and real column names are fed back to the model, up to 5 attempts, and a
KPI that still fails after that shows its full attempt history rather than a single opaque
error.
Verified: 2 of 5 CFPB KPIs failed on first attempt (a column name quoting issue) and succeeded
on the second attempt after the fix loop ran.

**Story 4, ROI numbers:**
Given the existing Round 1 cost estimate,
when Round 2's incremental build cost is added and a 24-onboarding-per-year volume assumption is
applied,
then ROI is calculated at 12 and 36 months using the required formula, with a break-even note.
Verified: 119% (12 months), 381% (36 months), about 5 months to break even, all shown with
their assumptions, not just as bare numbers.

**Story 9, ingesting genuinely semi-structured data:**
Given a source where records are deeply nested JSON and even the top-level schema is not
consistent record to record,
when a loader converts it into relational tables,
then the pipeline's existing profiling, FK detection, and model/KPI generation all run against
it unchanged, no pipeline code has to know the source was ever JSON.
Verified: Open Food Facts converted into `products`, `ingredients`, `categories`, and
`nutriments` tables, all three child-to-parent relationships confirmed at 100% value overlap,
and the AI proposed a genuine star schema (`nutriments` as fact, the other three as dimensions)
grounded in those real relationships. Finding a real bug along the way: foreign key detection
required an exact column name match and missed all three relationships until that was fixed,
see `pipeline/pipeline_documentation.md`.

**Story 5, compliance sign-off:**
Given the Act's four-tier risk framework and GDPR's controller/processor roles,
when this project's actual data flow is walked through step by step,
then a defensible risk classification and a data flow map are produced, not a generic
boilerplate disclaimer.
Verified: classified minimal risk under the AI Act, with the specific Annex III categories ruled
out one by one, and a GDPR processing register covering every step from client export to
delivered report.

## Sprint plan and timeline

One sprint, Monday August 31 to Thursday September 3, 2026. Friday September 4 is presentation
day, not build time.

| Day | Planned | What actually happened |
|---|---|---|
| 1, Mon Aug 31 | `feedback/round1_decision.md`, `use_case_definition.md`, start the PII check | All done, plus `pipeline_documentation.md`'s limits section and the README's setup step, pulled forward from day 2 |
| 2, Tue Sep 1 | Finish the PII integration, load the full CFPB dataset, `roi_risk_assessment.md` | All done: loaded the full 17.4 million row CFPB dataset, reworked `profiling.py` to sample large tables safely so profiling stays fast at that size, rebuilt the dashboard's ERD, and added a 5-attempt KPI SQL retry loop. `roi_risk_assessment.md` shipped the same day |
| 3, Wed Sep 2 (today) | `compliance/eu_ai_act_compliance.md`, `compliance/gdpr_documentation.md`, `strategic_plan.md`, `delivery_plan.md` | All done, plus `mvp_documentation.md` and `README.md`'s Round 2 update pulled forward from day 4, and a third dataset, Open Food Facts, streamed and converted from nested JSON into relational tables, which found and fixed a real gap in foreign key detection (required an exact column name match, missed real relationships that used a different naming convention on each side). Started day 4's items early, same day |
| 4, Thu Sep 3 | No-code POC, presentation content, full checklist review | Started ahead of schedule, on day 3 |
| Fri Sep 4 | Presentation prep and delivery | Not build time |

The "What actually happened" column is kept alongside "Planned" on purpose, rather than
collapsed into one column. An AI Manager's delivery record should show what was actually built
each day, not just a plan restated as if it were a log.
