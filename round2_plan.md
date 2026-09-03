# Round 2 Build Plan: Data Copilot

## Context

Round 1 built a Python pipeline (profiling, then AI data model/KPI generation, then insights)
for Chleo's boutique data consultancy. It was demoed on the clean, relational Olist e-commerce
dataset. `feedback/round1_decision.md` records the decision to keep this use case for Round 2
and adds two extensions. First, test the pipeline against messier, free-text-heavy data.
Second, add a data quality check that looks for private data inside free text fields, not just
in structured columns.

This project also serves as evidence for an AI Manager certification. So on top of the 8
standard Round 2 deliverables (`additional/Capstone-Round-2.docx`), the teacher asked for
explicit delivery-management artifacts: user stories, definition of done, acceptance criteria,
a sprint plan, and a timeline. These artifacts document how the Round 2 work itself was
planned and run. That is the AI Manager's own deliverable: scoping, risk and compliance
ownership, stakeholder communication, delivery cadence. This is separate from
`strategic_plan.md`, which covers the product's go-to-market timeline, not the build process.

**Confirmed decisions (from user):**
- Second dataset: **CFPB Consumer Complaint Database**. Free-text complaint narratives, messy,
  semi-structured, a second industry vertical (financial services) to test generalization.
- PII detection: **Presidio** (`presidio-analyzer` + `presidio-anonymizer`, local spaCy model).
  Free, MIT licensed, runs entirely locally, no API calls.
- Deadline: all deliverables done by **end of Thursday, Sep 3, 2026**. Friday, Sep 4 is
  presentation prep and delivery, not build time. One sprint, Mon Aug 31 to Thu Sep 3.

**A real bug this work fixes:** `pipeline/profiling.py::profile_table` currently samples the
first 3 unique values of every column, including free-text ones. Then
`model_kpi_generator.py::summarize_profile` puts those raw samples straight into the prompt sent
to OpenAI. Today this stays latent, since Olist's tables do not push much raw free text through
that path. But the CFPB narrative column would trigger it directly: real complaint text,
possibly containing names or emails, would get sent to OpenAI as a "sample value." Round 2 fixes
this. PII detection runs locally first, and any sample value shown to the LLM (or saved to
`outputs/profiling.json`) is redacted first. This becomes a concrete, creditable finding for the
GDPR and EU AI Act docs.

## Deliverable-by-deliverable plan

### 1. `use_case_definition.md` (root)
A write-up task, not new research. Pull from `research/sector_research.md` and
`research/use_cases.md`, which already cover the problem, company profile, and stakeholders.
Add: 2 or more measurable success criteria (for example "cut new-client onboarding profiling
and first-draft time from 4 to 8 hours down to under 1 hour", "flag 100% of free-text columns
containing detectable PII before a report reaches a client"), out-of-scope boundaries (no
autonomous client-facing delivery, no support for non-tabular sources like PDFs or scans), and
an "evolution from Round 1" section pointing at `feedback/round1_decision.md`.

### 2. Text quality checks: free text PII + categorial consistency (code, new)
New file **`pipeline/text_quality.py`**:
- `is_free_text_column(series) -> bool`: a heuristic on average string length and distinct
  ratio. Short, low-cardinality text counts as categorical. Long, high-cardinality text counts
  as free text.
- `scan_column_for_pii(series) -> dict`: runs Presidio's `AnalyzerEngine` locally over non-null
  values, and tallies counts and percentages per entity type (PERSON, EMAIL_ADDRESS,
  PHONE_NUMBER, LOCATION, CREDIT_CARD, IBAN_CODE). It never returns the raw matched text, only
  aggregate counts, so even `outputs/profiling.json` stays safe to share.
- `redact_sample(value) -> str`: uses Presidio's `AnonymizerEngine` to mask detected entities
  (for example `<PERSON>`, `<EMAIL_ADDRESS>`) in any string before it is used as a sample value.
- `check_casing_consistency(series) -> dict`: for non-free-text string columns, groups values by
  their lowercased form and flags when the same value appears in more than one casing or
  spacing variant (for example "Active", "active", "ACTIVE"). This directly closes a gap already
  named in `pipeline/pipeline_documentation.md`: outlier detection only applies to number
  columns, and text quality problems like inconsistent casing were not caught before.
- Defensive fallback: if the `presidio` import fails, fall back to a small regex check (email
  and phone only) and print a clear warning. This matches the existing LangSmith fallback
  pattern already in `model_kpi_generator.py`.

Wire into **`pipeline/profiling.py`**:
- In `profile_table`, for each column, call `is_free_text_column`. If true, add a
  `free_text_pii` block to that column's stats (entity counts and percentages), and pass
  `sample_values` through `redact_sample` before storing them. This replaces the current
  unconditional raw sampling.
- If false (a categorical string column), call `check_casing_consistency` and add a
  `casing_issues` block when any are found.
- No other structural changes. Duplicate and numeric outlier logic stays as is.

Wire into **`pipeline/model_kpi_generator.py`**: no prompt logic changes needed once
`profiling.py` only ever hands it redacted samples, since `summarize_profile` already just
prints whatever `sample_values` contains. Add one line to `MODEL_KPI_PROMPT`'s quality-findings
instruction so the AI explicitly calls out any column flagged with detected PII or casing
issues in its quality findings list.

Surface in **`dashboard/app.py`**: in the "Checks performed" table (already table by table), add
a "Free text PII flags" column and a "Casing issues" column, shown when a table has any.

### 3. Second dataset: CFPB Consumer Complaints
- New loader: **`pipeline/load_cfpb_data.py`**, following the same pattern as `load_data.py`:
  read CSV file(s) into SQLite. Download a manageable slice from the CFPB bulk download (for
  example the last 12 months, or a single product category), and save it to `data/cfpb/`. This
  size limit matters. See item 4 below on data volume limits.
- Point `DB_PATH` at a second database file (`data/warehouse_cfpb.db`) instead of merging into
  the Olist warehouse, since these are two separate "clients," not one schema. Add a small
  `--db` option or env var to `profiling.py` and `run_pipeline.py` so the same pipeline code
  runs against either warehouse, without duplicating any pipeline logic.
- Run the full pipeline against it once locally, to confirm it produces a sane report end to
  end. This is also the generalization proof for the open risk already named in
  `research/opportunities_risks.md`.

### 4. Update "Limits compared to a production version" in `pipeline/pipeline_documentation.md`
This section already lists Round 1's known gaps honestly. Round 2 should update it, not just
add new files elsewhere, so the documentation stays accurate about what changed and what did
not.

- **KPI SQL failures are still caught and shown, not retried.** Stays a known limit for Round 2.
  Note it as a pilot-phase hardening item in `strategic_plan.md` (feed the SQL error back to the
  model and retry).
- **Still no caching or cost control on repeated runs.** Stays a known limit. Note it as a
  pilot-phase hardening item too. Cost impact stays small at current volume, per
  `cost_estimation/cost_analysis.md`, so this is not urgent yet.
- **Still only one LLM provider (OpenAI), no fallback.** Stays a known limit. Note it as a
  full-deployment hardening item, and add it as a vendor lock-in risk in
  `roi_risk_assessment.md`.
- **Data volume: still pandas in memory.** The CFPB slice used for Round 2 must be sized to fit
  comfortably in memory, the same way Olist was. Document this directly: the CFPB test was
  deliberately sized down, not proof the volume limit is gone. The DuckDB upgrade path named in
  Round 1 still stands for a client with tens of millions of rows.
- **Data structure, rewritten with more precision:**
  - "Unstructured data does not work as-is" gets split into two claims. Free text *inside* an
    otherwise structured export (a comment column, a narrative field) is now handled by item 2
    above. Fully unstructured sources (PDFs, scanned documents, deeply nested JSON) are still
    out of scope and still need a separate conversion step first.
  - "The data model recommendation needs real multi-table data to be useful" stays true. The
    CFPB slice may end up as one table or close to it, so the model recommendation step may have
    little to model there. That is an expected result of testing on this dataset, not a bug to
    fix.
  - "Foreign key detection relies on naming conventions" stays unchanged.
  - "Outlier detection only applies to number columns" stays true for the numeric check
    specifically, but is now narrowed by item 2's two new checks (free text PII, and casing
    consistency for categorical text).

### 5. `roi_risk_assessment.md` (root)
Reformat existing numbers, this is not new research. `cost_estimation/cost_analysis.md` already
has the upfront cost (3,040 EUR), the ongoing cost per run (about 48 EUR), and the value saved
per onboarding (380 to 760 EUR). Add: ROI percent at 12 and 36 months, using
`(Net Benefit / Total Cost) x 100`, an assumptions table, and a break-even note. Expand
`research/opportunities_risks.md`'s risk table to 6 or more risks, covering regulatory,
technical, ethical, and operational categories, each with likelihood (1 to 5), impact (1 to 5),
and a mitigation. Add the free-text PII risk, the CFPB generalization result, and the vendor
lock-in risk from item 4 as new entries.

### 6. `compliance/eu_ai_act_compliance.md`
Classification reasoning: this is an internal decision-support draft, reviewed by a human before
any client sees it. It does not touch Annex III high-risk categories (employment, credit
scoring, biometric ID, essential services access). So it classifies as **minimal or limited
risk**, with the main obligation being transparency: disclosing that the report content is AI
generated. Include the step-by-step reasoning, a mandatory requirements summary, a short
conformity assessment summary, and a technical documentation outline (a table of contents only,
per the brief).

### 7. `compliance/gdpr_documentation.md`
A data flow map: client export, into SQLite, through the local PII scan, into a redacted
profile, into OpenAI, back as a report, then a consultant review, then the client. A processing
activities register. A short DPIA focused on the two highest-risk steps: first, any raw client
data reaching OpenAI, mitigated by the fix in item 2 (document this fix explicitly as a DPIA
control), and second, the cross-border transfer to OpenAI's US infrastructure (note the SCCs,
and the `LANGSMITH_ENDPOINT` EU data residency option already present in `.env.example`, as a
related existing control). Then data subject rights support, and a third-party and cross-border
transfers section.

### 8. `strategic_plan.md` (root)
Phases: POC (what exists now), then Pilot (run on 2 to 3 real consultancy clients, with a
mandatory human review gate before any client sees output), then Full deployment (embedded into
Chleo's service offering), then an optional Scale phase (licensed to other boutique
consultancies). Include timeline and milestones, go-to-market details (buyers: boutique
consultancy owners; channel: direct outreach and community; pricing: an internal efficiency tool
first, a licensed SaaS product as a stretch goal), a stakeholder communication plan, KPIs per
phase (including what greenlights the move from pilot to full deployment), and the
commercialisation model. Fold in the pilot-phase and full-deployment hardening items named in
item 4.

### 9. `delivery_plan.md` (root, new: the AI Manager artifacts)
One file covering all five required pieces, framed clearly as "how this Round 2 sprint was
planned and run":
- **User stories**: one per major deliverable or feature, written from the relevant role
  (Chleo, the consultant, the client, and the AI Manager as the delivery owner). For example:
  "As a consultant, I want free-text fields flagged for detected PII before a report reaches a
  client, so I don't accidentally expose personal data."
- **Definition of done**: concrete and checkable. For example: "every required file from the
  Round 2 checklist exists and is not empty," "the pipeline runs end to end on both datasets
  without crashing," "no raw PII appears in `outputs/*.json` or in any LLM prompt."
- **Acceptance criteria**: written as Given, When, Then, one set per user story.
- **Sprint plan**: the single sprint from Mon Aug 31 to Thu Sep 3, broken into 4 daily goals.
  See the Timeline table below.
- **Timeline**: the same 4 days, plus Friday as presentation day, shown as a simple table.

Start the file with a short paragraph explaining what an AI Manager role covers here: turning a
business problem into a scoped AI use case, owning risk and compliance sign-off, tracking ROI,
and running the delivery cadence. This makes clear why these artifacts sit alongside the
technical ones.

### 10. MVP (root `mvp_documentation.md`, no new app code duplication)
The Round 1 pipeline plus dashboard is already a working, end-to-end MVP. Rather than
duplicating it into a new `mvp/` folder, which would add structure the project does not need,
add **`mvp_documentation.md`** at root instead. It should point at `pipeline/` and `dashboard/`
as the MVP, list what is already there (a functional app, the core AI capability actually
running, and the defensive `.get()` pattern already in
`run_pipeline.py::execute_kpi_sql` as existing basic error handling), and document what Round 2
adds: the text quality and PII check, and CFPB dataset support. Add a small amount of new basic
error handling only where it is genuinely missing: in `load_cfpb_data.py`, and in
`text_quality.py`'s Presidio import fallback. Confirm `requirements.txt` includes
`presidio-analyzer` and `presidio-anonymizer`, and note the one-time
`python -m spacy download en_core_web_sm` step in both `README.md` and
`mvp_documentation.md`.

### 11. No-code/low-code POC (`poc/`)
Build a small **n8n** workflow that mirrors the pipeline conceptually, not a rebuild of the
Python logic: a webhook or file trigger, then an OpenAI node that takes a schema summary and
proposes KPIs, then an output step (a formatted message or an emailed report). Export the
workflow as `poc/poc_workflow.json`, take annotated screenshots, and write
`poc/poc_documentation.md` (the tools used, the steps, what AI capability it shows, and its
limits compared to the production Python pipeline: no real SQL execution, no PII scan,
illustrative only). The 2 to 5 minute demo recording needs to be recorded by the user directly.
I can write a script or shot list for it, but I cannot produce a screen recording myself.

### 12. Final presentation
`additional/build_pptx.py` already exists from Round 1 as a working deck-generation script, so
reuse that pattern instead of building a new one. I do not have the
`pf-05-project-presentation.md` template content, since it lives on the Ironhack LMS, not in
this repo. So I cannot confirm the exact required structure yet. Plan: draft slide content
covering all Round 2 deliverables now, then adjust the structure once the template is found.
This is an open item, not a blocker for everything else.

## Sprint plan / Timeline

| Day | Date | Focus |
|---|---|---|
| 1 | Mon Aug 31 (today) | `feedback/round1_decision.md` (done), `use_case_definition.md`, start `text_quality.py` and the Presidio integration |
| 2 | Tue Sep 1 | Finish the PII integration and the redaction fix in `profiling.py`, the CFPB loader and first full pipeline run on it, `roi_risk_assessment.md` |
| 3 | Wed Sep 2 | `compliance/eu_ai_act_compliance.md`, `compliance/gdpr_documentation.md`, `strategic_plan.md`, `delivery_plan.md` |
| 4 | Thu Sep 3 | n8n POC and `poc_documentation.md`, `mvp_documentation.md`, presentation slide content, full checklist review against `additional/Capstone-Round-2.docx` |
| Fri Sep 4 | (none) | Presentation prep and delivery, not build time |

## Verification

- `python pipeline/load_data.py && python pipeline/run_pipeline.py && streamlit run dashboard/app.py`
  still works unchanged on Olist. This is a regression check.
- `python pipeline/load_cfpb_data.py && python pipeline/run_pipeline.py --db data/warehouse_cfpb.db`
  (or the equivalent) runs end to end, and produces a `report.json` with populated
  `free_text_pii` findings on the narrative column.
- Manually inspect `outputs/profiling.json` after a CFPB run, to confirm no raw PII string
  appears anywhere in the file. Only entity-type counts and redacted samples should be there.
- Temporarily print the exact prompt text sent in `generate_model_and_kpis` once, against CFPB
  data, to directly confirm the sample values reaching OpenAI are redacted, not raw.
- Walk the Round 2 submission checklist in `additional/Capstone-Round-2.docx` file by file
  against the repo before Thursday's deadline.
