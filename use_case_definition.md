# Use Case Definition

## Business problem statement

Chleo runs a small data analytics consultancy. Every new client starts the same way: a raw
data export lands on a consultant's desk, and someone has to manually check its quality, work
out how the tables relate, decide on a data model, pick the right KPIs, and write a first draft
"here is what your data tells us" report. This takes a senior consultant an estimated 4 to
8 hours per client, and it does not scale. Chleo also worries that handing this work to "the AI" means
losing the ability to explain a result back to a client, or to catch it when the AI gets
something wrong, including missing private data hidden inside free text fields.

## Company profile

- **Industry:** Data and analytics consulting services (B2B, serves clients across sectors).
- **Size:** Small, boutique consultancy, about 10 to 30 people.
- **Current state:** Every new client onboarding is done by hand. Profiling, modeling, and KPI
  selection reset from zero for each client. There is no shared tooling that carries lessons
  from one client engagement to the next.

## Proposed AI solution and system type

A "Data Copilot" pipeline that takes a new client's raw data export and produces, end to end: a
data quality and schema profile (including a check for private data inside free text fields), an
AI recommended data model, a set of business KPIs computed for real against the data, and a plain
language insight report. Every AI decision is logged (LangSmith) so a consultant can review it,
not just trust it.

**System type:** decision-support, not autonomous. The output is always a first draft for a
consultant to review before it reaches a client. The AI never sees raw client rows, only a
compact, PII-redacted schema summary for the model/KPI recommendation step, and already-computed
KPI numbers for the insight-writing step.

## Key stakeholders and interests

| Stakeholder | Interest |
|---|---|
| Chleo (company owner) | More billable capacity without hiring, and a system she can explain to clients, not a black box |
| Consultants | A fast, reliable first draft they can check quickly, with clear visibility into where the AI got something wrong |
| Clients (the consultancy's customers) | A fast, accurate first read on their data, and confidence that their business and any personal data inside it is handled responsibly |
| Data subjects inside a client's export | Not part of the engagement directly, but their personal data (names, emails, and so on) may appear inside a client's raw export, especially in free text fields, and needs protecting under GDPR |

## Success criteria

1. Cut new-client onboarding time (profiling plus a first-draft report) from an estimated 4 to
   8 hours down to under 1 hour of consultant time per client. The 4 to 8 hours is an estimate;
   the pilot measures the real baseline first (story P1 in `delivery_plan.md`).
2. Flag 100% of free-text columns that contain detectable PII (email address, phone number,
   person name, and similar) before any report reaches a client. Verified by testing on Olist,
   CFPB, and Open Food Facts.
3. Run end to end, without crashing, on structurally different datasets: Olist's clean
   relational e-commerce data, CFPB's messier, free-text-heavy financial complaints data (tested
   at its full size, 17.4 million rows, not a small slice), and Open Food Facts' genuinely
   semi-structured JSON, converted into relational tables. This is the direct test of the
   generalization risk raised in `research/opportunities_risks.md`, across three different data
   shapes, not one.

## Out-of-scope boundaries

- No autonomous client-facing delivery. Every report needs a human consultant review before it
  reaches a client.
- No support for fully unstructured sources (PDFs, scanned documents, images) as-is. Those need
  a separate conversion step before this pipeline can run on them, the same kind of step
  `load_generic_json.py` handles for nested JSON, but not written for these other formats.
- No fallback to a second LLM provider. Documented as a hardening item for the
  full-deployment phase, see `pipeline/pipeline_documentation.md` and `strategic_plan.md`.
  (Failed KPI SQL is in scope: it is retried up to 5 times against the model itself, see
  `pipeline/pipeline_documentation.md`'s limits section.)
- No true production-scale data volume handling everywhere. The pipeline was tested successfully
  against the full CFPB dataset (17.4 million rows), which works because `profiling.py` samples
  large tables instead of loading them whole into pandas. But this fix is not everywhere:
  foreign key detection between large related tables still loads full columns into Python to
  check value overlap. CFPB never exercised that code path, since it is one table, but Open Food
  Facts did, at a smaller scale (25,000 products across 4 tables), and worked. See
  `pipeline/pipeline_documentation.md`'s "Data volume" section for exactly what was and was not
  tested at what scale.
- No fully reliable AI-proposed schema yet. `load_generic_json.py` converts nested JSON to
  relational tables by having the AI propose the structure, used for Open Food Facts instead
  of a hand-written loader. Testing found it is not fully reproducible run to
  run, even at temperature 0, mitigated by asking 3 times and taking the union
  (`propose_flattening_plan_consensus`), not eliminated. See
  `pipeline/pipeline_documentation.md`'s "AI-proposed schema" section.

## How the solution was tested

Three public datasets stand in for three different kinds of new client data:

1. **Olist Brazilian E-Commerce:** clean and relational, about 1.5 million rows.
2. **CFPB Consumer Complaints:** messy, mostly a single flat table, full of free text, tested at
   its full real size (17.4 million rows). This shows the pipeline holds up on large data.
3. **Open Food Facts:** semi-structured JSON, where even the top-level fields change from record
   to record. A loader converts it into 4 relational tables, with the schema proposed by the AI.

Personal data protection is part of the design: PII detection runs locally first, and any
sample value shown to the LLM, or saved to `outputs/profiling.json`, is redacted before it
leaves the machine.
