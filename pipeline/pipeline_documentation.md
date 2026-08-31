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

## What this proves, and what it does not

**It proves:** the pipeline can take a genuinely messy multi table export it has never seen
before, and produce a reasonable first draft model, KPI set, and quality assessment, with every
AI decision logged and reviewable in LangSmith.

**It does not prove:** that this works reliably across every possible client schema (Round 1
only tested one dataset, see the generalization risk in `research/opportunities_risks.md`), or
that the AI recommended model is always the best one a senior consultant would pick. It is a
fast first draft for a consultant to review, not a replacement for that review.

## Limits compared to a production version

- KPI SQL failures are caught and shown, not silently retried or fixed. A production version
  would likely feed the SQL error back to the model and try again.
- There is no caching or cost control on repeated runs.
- Only one LLM provider (OpenAI) is used, with no fallback option.

### Data volume

The AI step stays cheap and fast no matter how big the data is, since it only ever sees a
compact schema summary (column names, types, null percentages, a few sample values), never raw
rows. The parts that would not hold up against much bigger data are the profiling and loading
steps: `load_data.py` and `profiling.py` both pull whole tables into memory with pandas, and
foreign key detection loads full columns into Python to check value overlap. That is fine at
Olist's scale (roughly 1.5 million rows across all tables), but would need rework for a client
with tens of millions of rows or multi-gigabyte files: push the quality checks down into SQL
aggregate queries instead of pandas, and move off SQLite onto something built for larger
analytical data, DuckDB being the most direct upgrade path.

### Data structure

The pipeline assumes tabular, relational data (CSV-shaped tables in a SQL database). A few
structural assumptions worth being upfront about:

- **Unstructured data does not work as-is.** A client whose raw data is PDFs, scanned
  documents, free text logs, or deeply nested JSON would need a separate step to turn that into
  tables before this pipeline could run at all.
- **The data model recommendation needs real multi-table data to be useful.** A client handing
  over one flat spreadsheet still gets quality checks and KPIs, but there is nothing to model,
  since there are no relationships between tables to find.
- **Foreign key detection relies on naming conventions** (columns ending in `id`), confirmed by
  checking real value overlap. A schema using very different key naming could have real
  relationships the pipeline does not notice.
- **Outlier detection only applies to number columns.** Text quality problems, like
  inconsistent casing or mixed formats in a status column, are not caught by that specific
  check, though null and duplicate checks apply to every column regardless of type.
