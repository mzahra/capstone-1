# POC / Pipeline Documentation

n8n was not used. The whole POC is a small Python pipeline. This fits a single stack, 1 day
build better, and it shows the actual data engineering skill (profiling, modeling) directly,
instead of through a workflow builder UI.

## What it does

1. **Loaders**, one per "client," each simulating a raw export landing on a consultant's desk:
   - `load_data.py`: every CSV in `data/` into a local SQLite database (Olist).
   - `load_cfpb_data.py`: streams the full CFPB bulk export into SQLite in chunks (17.4 million
     rows), never a small slice.
   - `load_openfoodfacts_data.py`: streams a bounded slice of Open Food Facts' nested JSON
     export and flattens each product into relational tables (`products`, `ingredients`,
     `categories`, `nutriments`), the conversion step Round 1 said this pipeline did not have.
2. **`profiling.py`**: computes quality stats per table and column (nulls, duplicates,
   outliers, free text PII, casing consistency), finds primary key candidates, and finds foreign
   key candidates across tables, confirmed by checking real value overlap, not just matching
   column names. Samples large tables instead of loading them whole, see "Data volume" below.
3. **`model_kpi_generator.py`**: makes two LLM calls.
   - Given the profile, it proposes a data model plus a KPI list with SQL, the top quality
     issues, and some data science opportunities.
   - Given the KPI results after they are actually run, it writes plain language business
     insights.
   - Also fixes a failed KPI's SQL on request, see "Limits compared to a production version"
     below.
4. **`run_pipeline.py`**: runs all of the above end to end and writes a report JSON file, which
   `dashboard/app.py` then displays. Takes `--db` and `--out` so the same code runs against any
   of the three warehouses.

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

**It does not prove:** that this works reliably across every possible client schema. Round 2
tested three structurally different datasets (Olist's clean relational tables, CFPB's messy
single flat table, Open Food Facts' genuinely nested JSON converted into relational tables), see
the generalization risk in `research/opportunities_risks.md`, but three is not every shape a
real client's data could take. Nor does this prove the AI recommended model is always the best
one a senior consultant would pick. It is a fast first draft for a consultant to review, not a
replacement for that review.

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

**Round 2 status: partly fixed, tested at real scale.** The CFPB test uses the full export: about 17.4 million rows, about 30 GB as CSV, well past Olist's roughly 1.5
million rows. This tests the volume limit directly, instead of staying inside it.

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

The pipeline itself only ever reads tabular data (tables in a SQL database). What changed in
Round 2 is what can get a client's data into that shape in the first place, tested against two
more datasets on top of Olist: CFPB Consumer Complaints (messy, mostly one flat table, free text
heavy) and Open Food Facts (genuinely semi-structured JSON, converted into relational tables).

- **Free text inside a structured export is handled. Genuinely nested JSON now has a working
  conversion path too, for one real case. Fully unstructured sources still do not.** Round 1
  said "unstructured data does not work as-is" for all three of these together. Round 2 splits
  the claim in two ways. First, a comment or narrative column inside an otherwise tabular export
  (the CFPB complaint narrative, or Olist's review text) is profiled for quality and scanned for
  PII, see `text_quality.py`. Second, `load_openfoodfacts_data.py` takes Open Food Facts' deeply
  nested JSON, where even the top-level fields are not consistent record to record, and flattens
  each product into a `products` row plus child rows in `ingredients`, `categories`, and
  `nutriments` tables. That is a real, working conversion step for that one source's shape, not
  a general JSON importer. Fully unstructured sources (PDFs, scanned documents, images) are
  still out of scope, and still need a separate conversion step written for them too.
- **The data model recommendation needs real multi-table data to be useful, and now has some to
  work with beyond Olist.** CFPB's single flat table produced a thin recommendation, as expected
  for that shape of data, not a bug. Open Food Facts, converted into four real related tables,
  produced a genuine star schema recommendation instead (`nutriments` as the fact table,
  `products`/`categories`/`ingredients` as dimensions), grounded in real, confirmed foreign keys,
  see below.
- **Foreign key detection no longer requires an exact column name match.** Fixed in Round 2.
  It used to require the child and parent column to share the exact same name (for example both
  sides named `customer_id`), and only consider names ending in `id`. Confirmed as a real gap
  using Open Food Facts: its child tables use `product_code` against the parent's `code` column,
  a real relationship, 100% value overlap, that the old version found nothing for. Fixed by
  broadening the name hint to any column containing "id", "code", "key", or "ref", and matching
  against any of the other table's primary key candidates, not just an identically named one.
  The actual relationship is still only ever confirmed by real value overlap, the name hint is
  just a cheap way to avoid checking every column against every other table's keys. Regression
  checked against Olist: same 7 relationships found, before and after.
- **Outlier detection only applies to number columns.** Still true for the numeric check
  specifically. But this is now narrowed by Round 2's two new text checks (PII detection and
  casing consistency, see above), rather than text quality being uncovered entirely.
- **PII detection accuracy depends on the text's language.** New in Round 2. The PII scan uses
  an English spaCy model (`en_core_web_sm`). On non-English free text, such as Olist's
  Portuguese review comments, it still finds real matches, but with more missed and false
  matches than on English text. A production version serving non-English clients would need a
  language-matched model.
