# POC / Pipeline Documentation

n8n was not used. The whole POC is a small Python pipeline. This fits a single stack, 1 day
build better, and it shows the actual data engineering skill (profiling, modeling) directly,
instead of through a workflow builder UI.

## What it does

1. **`load_data.py`**: loads every CSV in `data/` into a local SQLite database. This simulates
   a raw client export landing on a consultant's desk.
2. **`profiling.py`**: computes quality stats per table and column (nulls, duplicates,
   outliers), finds primary key candidates, and finds foreign key candidates across tables,
   confirmed by checking real value overlap, not just matching column names.
3. **`model_kpi_generator.py`**: makes two LLM calls.
   - Given the profile, it proposes a data model plus a KPI list with SQL, the top quality
     issues, and some data science opportunities.
   - Given the KPI results after they are actually run, it writes plain language business
     insights.
4. **`run_pipeline.py`**: runs all of the above end to end and writes `outputs/report.json`,
   which `dashboard/app.py` then displays.

## Where the AI is actually called

There are exactly 2 AI calls in the whole project, both in `model_kpi_generator.py`, both
called from `run_pipeline.py`. Everything else, loading data, profiling, running SQL, and the
dashboard, is deterministic Python and SQL, no AI involved.

| Step | File | AI call? | What happens |
|---|---|---|---|
| 1. Load data | `load_data.py` | No | CSVs into SQLite |
| 2. Profile | `profiling.py` | No | pandas: nulls, duplicates, outliers, key detection |
| 3. Recommend model + KPIs | `model_kpi_generator.py`, `generate_model_and_kpis()` | Yes, call #1 | Input: the schema profile (text summary). Output: fact/dimension model, KPI list with SQL, quality findings, data science ideas |
| 4. Execute KPIs | `run_pipeline.py` | No | The SQL from step 3 is run for real against SQLite, pure database execution, no AI |
| 5. Write insights | `model_kpi_generator.py`, `generate_insights()` | Yes, call #2 | Input: the KPI results (real numbers) plus the quality findings. Output: plain language business insights |
| 6. Dashboard | `dashboard/app.py` | No | Just reads and displays the JSON that steps 1 to 5 produced |

The AI never sees raw client data, rows, or individual records.
Call #1 only sees a compact schema and stats summary, and call #2 only sees already computed KPI
numbers. This is also why the AI step stays cheap and fast regardless of dataset size, see
"Data volume" below.

## What this proves, and what it does not

**It proves:** the pipeline can take a genuinely messy multi table export it has never seen
before, and produce a reasonable first draft model, KPI set, and quality assessment, with every
AI decision logged and reviewable in LangSmith.

**It does not prove:** that this works reliably across every possible client schema (Round 1
only tested one dataset, see the generalization risk in `research/opportunities_risks.md`), or
that the AI recommended model is always the best one a senior consultant would pick. It is a
fast first draft for a consultant to review, not a replacement for that review.

## Limits compared to a production version

This section is reviewed every round, so it stays accurate about what changed and what did not.
Round 2 status is marked next to each point.

- **KPI SQL failures are now retried, not just shown.** Fixed in Round 2. `execute_kpi_sql` in
  `run_pipeline.py` retries a failed KPI up to `MAX_KPI_ATTEMPTS` (5) times: the exact SQLite
  error and the real column names are fed back to the model via
  `model_kpi_generator.fix_kpi_sql`, which is asked to correct the query. This matters most for
  column names with spaces or punctuation, like CFPB's `"Timely response?"`, which the AI
  sometimes rewrites into a clean-looking name that does not exist, like `Timely_response`. A
  KPI that still fails after 5 attempts is shown with its full attempt history
  (`attempt_errors` in the report), not hidden. See the dashboard's "KPI(s) failed to compute"
  section.
- **Still no caching or cost control on repeated runs.** Unchanged in Round 2. Cost stays small
  at current volume, see `cost_estimation/cost_analysis.md`, so this is not urgent yet. Also
  kept as a pilot-phase hardening item.
- **Still only one LLM provider (OpenAI), with no fallback.** Unchanged in Round 2. Kept as a
  full-deployment hardening item, and listed as a vendor lock-in risk in
  `roi_risk_assessment.md`.
- **Round 2 adds two new checks that did not exist before:** a local PII scan on free text
  columns, and a casing/format consistency check on categorical text columns. Both live in
  `pipeline/text_quality.py`. Neither sends raw text to OpenAI: PII detection and redaction both
  run locally first, see the "Where the AI is actually called" table above.

### Data volume

The AI step stays cheap and fast no matter how big the data is, since it only ever sees a
compact schema summary (column names, types, null percentages, a few redacted sample values),
never raw rows.

**Round 2 status: partly fixed, tested at real scale.** The original plan was to keep the CFPB
test to a small, date-filtered slice, the same way Round 1 stayed within Olist's roughly 1.5
million rows. That plan changed: the full CFPB export was loaded instead, about 17.4 million
rows, about 30 GB as CSV, to genuinely test this limit rather than avoid it.

- **Loading:** `load_cfpb_data.py` streams the CSV out of the zip in 100,000-row chunks straight
  into SQLite, never holding more than one chunk in memory. This part scales fine, since SQLite
  is disk-based, not memory-based. Loaded in about 15 minutes.
- **Profiling:** `profiling.py`'s `profile_table` used to pull a whole table into a pandas
  DataFrame, which was the real limit. It now checks the true row count first with a plain SQL
  `COUNT(*)`, and above `SAMPLE_ROW_THRESHOLD` (100,000 rows), pulls an evenly spaced sample
  instead of the whole table for the per-column stats (nulls, outliers, PII scan, casing
  check). Row counts stay exact either way. Profiled the full 17.4 million row table in about
  90 seconds.
- **KPI execution:** unaffected by any of this, since `execute_kpi_sql` in `run_pipeline.py`
  always ran the generated SQL as a real aggregate query against the full table in SQLite, never
  through pandas. The KPI numbers in the CFPB report (for example, 11.9 million complaints in
  the top product category) are computed from all 17.4 million rows, not a sample.
- **What is still not fixed:** foreign key detection (`detect_fk_candidates`) still loads full
  columns into Python to check value overlap between tables. This did not matter for CFPB, which
  is one table, so that code path never ran. It would still need the same sampling treatment for
  a future client with several large, related tables. Primary key detection also only checks
  uniqueness within the sample for a sampled table, not the true full table, so it is a
  reasonable candidate, not a guarantee, at this scale.

### Data structure

The pipeline assumes tabular data (CSV-shaped tables in a SQL database). A few structural
assumptions worth being upfront about, updated after testing against a second, messier dataset
in Round 2 (CFPB Consumer Complaints):

- **Free text inside a structured export is now handled, fully unstructured sources are not.**
  Round 1 said "unstructured data does not work as-is" for both cases together. Round 2 splits
  this claim. A comment or narrative column inside an otherwise tabular export (like the CFPB
  complaint narrative, or Olist's review text) is now profiled for quality and scanned for PII,
  see `text_quality.py`. Fully unstructured sources, PDFs, scanned documents, images, or deeply
  nested JSON, are still out of scope, and still need a separate conversion step first.
- **The data model recommendation still needs real multi-table data to be useful.** Unchanged.
  A client handing over one flat table still gets quality checks and KPIs, but there is nothing
  to model, since there are no relationships between tables to find. The CFPB slice tested in
  Round 2 is close to a single flat table, so its data model recommendation is expected to be
  thin. That is the expected result of testing on this shape of data, not a bug.
- **Foreign key detection relies on naming conventions** (columns ending in `id`), confirmed by
  checking real value overlap. Unchanged. A schema using very different key naming could have
  real relationships the pipeline does not notice.
- **Outlier detection only applies to number columns.** Still true for the numeric check
  specifically. But this is now narrowed by Round 2's two new text checks (PII detection and
  casing consistency, see above), rather than text quality being uncovered entirely.
- **PII detection accuracy depends on the text's language.** New in Round 2. The PII scan uses
  an English spaCy model (`en_core_web_sm`). On non-English free text, such as Olist's
  Portuguese review comments, it still finds real matches, but with more missed and false
  matches than on English text. A production version serving non-English clients would need a
  language-matched model.
