# POC / Pipeline Documentation

## What it does

1. **Loaders**, one per "client," each simulating a raw export landing on a consultant's desk:
   - `load_data.py`: every CSV in `data/` into a local SQLite database (Olist).
   - `load_cfpb_data.py`: streams the full CFPB bulk export into SQLite in chunks (17.4 million
     rows), never a small slice.
   - `load_generic_json.py`: for Open Food Facts' genuinely nested JSON. Instead of a human
     hand-writing which fields matter, the AI is shown only field names, types, and how often
     each field appears across the whole source (never a value), and proposes the relational
     schema itself. Deterministic code applies whatever it proposes. See "AI-proposed schema"
     below for why this approach was chosen over a hand-written loader, and its known limit.
2. **`profiling.py`**: computes quality stats per table and column (nulls, duplicates,
   outliers, free text PII, casing consistency), finds primary key candidates, and finds foreign
   key candidates across tables, confirmed by checking real value overlap, not just matching
   column names. Samples large tables instead of loading them whole, see "Data volume" below.
3. **`model_kpi_generator.py`**: every LLM call in the project lives here. Proposes a data
   model plus KPIs with SQL, writes plain language insights from the real KPI results, fixes a
   failed KPI's SQL on request, and (for Open Food Facts) proposes the relational schema itself.
4. **`run_pipeline.py`**: runs the profiling-through-insights flow end to end and writes a
   report JSON file, which `dashboard/app.py` then displays. Takes `--db` and `--out` so the
   same code runs against any of the three warehouses.

## Where the AI is actually called

| Step | File | AI call? | What happens |
|---|---|---|---|
| 1. Load data | a `load_*.py` script | Only for Open Food Facts | Raw export into SQLite |
| 2. Profile | `profiling.py` | No | pandas: nulls, duplicates, outliers, key detection |
| 3. Recommend model + KPIs | `model_kpi_generator.py`, `generate_model_and_kpis()` | Yes | Input: the schema profile (text summary). Output: fact/dimension model, KPI list with SQL, quality findings, data science ideas |
| 4. Execute KPIs | `run_pipeline.py` | No | The SQL from step 3 is run for real against SQLite |
| 4b. Fix a failed KPI's SQL | `model_kpi_generator.py`, `fix_kpi_sql()` | Yes, only on retry | Input: the real SQLite error and real column names. Up to `MAX_KPI_ATTEMPTS` (5) times per KPI |
| 5. Write insights | `model_kpi_generator.py`, `generate_insights()` | Yes | Input: the KPI results (real numbers) plus the quality findings |
| 6. Dashboard | `dashboard/app.py` | No | Just reads and displays the JSON steps 1 to 5 produced |
| Open Food Facts only: propose the schema | `model_kpi_generator.py`, `propose_flattening_plan()`, called 3 times by `load_generic_json.py`'s `propose_flattening_plan_consensus()` | Yes | Input: field names, types, and presence percentages, never a value. Output: a proposed main table + child tables, applied by deterministic code |

The AI never sees raw client data, rows, or individual records, in any of these calls.

Every one of these calls is also cost-tracked: `model_kpi_generator.py` logs the real
`prompt_tokens`/`completion_tokens` OpenAI returns on each response and prices them at
gpt-4o-mini's real rate ($0.15 per 1M input, $0.60 per 1M output), not an estimate.
`run_pipeline.py` resets that log at the start of a run and writes the total under `report["cost"]`;
`load_generic_json.py` does the same for its 3 schema-proposal calls, writing it into the saved
schema plan. See `roi_risk_assessment.md`'s Ongoing costs section for a real measured run.

## AI-proposed schema for Open Food Facts

Open Food Facts' raw export is genuinely semi-structured JSON: deeply nested, and even the
top-level fields are not consistent record to record. Two ways to turn that into relational
tables were tried:

1. A hand-written loader, choosing the table structure by hand, the same way Olist's and CFPB's
   loaders work.
2. An AI-proposed loader (`load_generic_json.py`): the AI proposes the schema itself, from the
   data's own structure, so a new JSON source does not need its own bespoke loader written for
   it.

The AI-proposed loader is the one actually used for this report. It generalizes further, but
testing found a real reliability gap: even at temperature 0, the same prompt against the same
data did not always propose the same schema, one run silently dropped the nutrient breakdown
table in favor of a much shallower one. This is mitigated, not eliminated, by asking 3 times and
taking the union of tables found (`propose_flattening_plan_consensus`). This still needs more
work (for example, validating a proposal against a fixed checklist, or a human review step)
before it should be trusted without review on a dataset nobody has looked at yet.

## What this proves, and what it does not

**It proves:** the pipeline can take a genuinely messy multi table export it has never seen
before, and produce a reasonable first draft model, KPI set, and quality assessment, with every
AI decision logged and reviewable in LangSmith.

**It does not prove:** that this works reliably across every possible client schema. Round 2
tested three structurally different datasets (Olist's clean relational tables, CFPB's messy
single flat table, Open Food Facts' genuinely nested JSON), see the generalization risk in
`research/opportunities_risks.md`, but three is not every shape a real client's data could take.
Nor does it prove the AI recommended model is always the best one a senior consultant would
pick. It is a fast first draft for a consultant to review, not a replacement for that review.

## Limits compared to a production version

This section is reviewed every round, so it stays accurate about what changed and what did not.

- **KPI SQL failures are retried, not just shown.** Fixed in Round 2. `execute_kpi_sql` retries
  a failed KPI up to `MAX_KPI_ATTEMPTS` (5) times, feeding the real SQLite error and real column
  names back to the model. A KPI that still fails shows its full attempt history, not hidden.
- **Still no caching or cost control on repeated runs.** Cost stays small at current volume, see
  `cost_estimation/cost_analysis.md`. Kept as a pilot-phase hardening item.
- **Still only one LLM provider (OpenAI), with no fallback.** Kept as a full-deployment
  hardening item, and listed as a vendor lock-in risk in `roi_risk_assessment.md`.
- **Round 2 adds two checks that did not exist before:** a local PII scan on free text columns,
  and a casing/format consistency check on categorical text columns, both in
  `pipeline/text_quality.py`. Neither sends raw text to OpenAI, both run locally first.

### Data volume

The AI step stays cheap and fast no matter how big the data is, since it only ever sees a
compact schema summary, never raw rows.

**Tested at real scale.** CFPB uses the full export, about 17.4 million rows, well past
Olist's roughly 1.5 million. `load_cfpb_data.py` streams the CSV into SQLite in 100,000-row
chunks. `profiling.py` samples any table above `SAMPLE_ROW_THRESHOLD` (100,000 rows) for its
per-column stats instead of loading it whole, row counts and KPI results stay exact either way.
Still not fixed: foreign key detection (`detect_fk_candidates`) loads full columns into Python
to check value overlap, which would need the same sampling treatment for a future client with
several large, related tables.

### Data structure

The pipeline itself only ever reads tabular data. What changed in Round 2 is what can get a
client's data into that shape in the first place.

- **Free text inside a structured export is handled. Genuinely nested JSON has a working
  conversion path too. Fully unstructured sources still do not.** A comment or narrative column
  inside an otherwise tabular export (CFPB's complaint narrative, Olist's review text) is
  profiled for quality and scanned for PII, see `text_quality.py`. Open Food Facts' deeply
  nested JSON is converted into relational tables by `load_generic_json.py`, see "AI-proposed
  schema" above. Fully unstructured sources (PDFs, scanned documents, images) are still out of
  scope.
- **The data model recommendation needs real multi-table data to be useful.** CFPB's single
  flat table produced a thin recommendation, as expected for that shape of data, not a bug.
  Open Food Facts, converted into several real related tables, produces a genuine star schema
  recommendation instead, grounded in real, confirmed foreign keys.
- **Foreign key detection no longer requires an exact column name match.** Fixed in Round 2,
  confirmed necessary by a real gap: Open Food Facts' child tables use `product_code` against
  the parent's `code` column, a real relationship the old exact-match version found nothing for.
  Broadened to any column containing "id", "code", "key", or "ref", matched against any of the
  other table's primary key candidates, still only ever confirmed by real value overlap.
  Regression checked against Olist: same 7 relationships found, before and after.
- **The same naming gap also broke chart grouping, fixed with three checks instead of one.** A
  chart once grouped products by their barcode (`product_code`), not readable, because the code
  only recognized "id" as an identifier, not "code". Checking for repeated values was not enough
  either: `product_code` repeats a lot inside the `ingredients` table (only about 11% unique
  there), so a plain uniqueness check missed it too. `run_pipeline.py` now checks three things,
  and skips the chart if any one is true: the column name looks like an identifier (id, code,
  ref), it is already a confirmed key somewhere else in the schema, or almost all its values are
  unique (only checked on tables with 100+ rows, so a small lookup table is not mistaken for an
  identifier just for being unique).
- **Outlier detection only applies to number columns**, narrowed but not replaced by the two
  new text checks above.
- **PII detection accuracy depends on the text's language.** The scan uses an English spaCy
  model (`en_core_web_sm`). On non-English free text, such as Olist's Portuguese review
  comments, it still finds real matches, with more missed and false matches than on English.
