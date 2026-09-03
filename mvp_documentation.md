# MVP Documentation

## What the MVP is

`pipeline/` plus `dashboard/`. There is no separate `mvp/` folder, the working pipeline and
dashboard already are the MVP, and duplicating them into another folder would just be dead
weight to keep in sync. This satisfies the brief's four requirements: a functional application
users can try, the core AI capability actually running, basic error handling, and this file plus
`requirements.txt` and `.env.example`.

## A functional application users can try

```bash
conda activate myenv
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp .env.example .env   # fill in OPENAI_API_KEY and LANGSMITH_API_KEY
```

Then any of:

```bash
python pipeline/load_data.py && python pipeline/run_pipeline.py --out outputs/report_olist.json   # Olist
python pipeline/load_cfpb_data.py && python pipeline/run_pipeline.py --db data/warehouse_cfpb.db --out outputs/report_cfpb.json   # CFPB
python pipeline/load_generic_json.py --jsonl data/openfoodfacts/raw_products.jsonl --db data/warehouse_openfoodfacts.db && python pipeline/run_pipeline.py --db data/warehouse_openfoodfacts.db --out outputs/report_openfoodfacts.json   # Open Food Facts
streamlit run dashboard/app.py
```

The dashboard opens in a browser, with a sidebar dropdown to switch between the three "clients"
the pipeline has been run against. It also works right away without running anything first, all
three `report*.json` files and their matching `profiling*.json` files are already committed, so
a user can try the app on a fresh clone before setting up any API keys at all. Full setup and
run instructions are in `README.md`, this file only summarizes them.

## Core AI capability actually runs

Two real OpenAI calls happen on every pipeline run, both in `pipeline/model_kpi_generator.py`,
both traced in LangSmith so they can be reviewed, not just trusted:

1. `generate_model_and_kpis`: given a redacted schema profile, proposes a data model, a KPI
   list with SQL, quality findings, and data science opportunities.
2. `generate_insights`: given the real, executed KPI numbers, writes the plain language report.

This is not a canned demo. The AI genuinely does the modeling and writing work, and it can be
seen failing and being corrected in real time: when a KPI's generated SQL does not run (for
example, CFPB's `"Timely response?"` column, which the AI first tried to reference as
`Timely_response`), `run_pipeline.py::execute_kpi_sql` sends the exact SQLite error back to the
model and asks it to fix the query, up to 5 attempts, calling `model_kpi_generator.fix_kpi_sql`.
Verified on the full CFPB run: 2 of 5 KPIs failed on the first attempt and succeeded on the
second, after the model saw its own error and corrected the column name.

## Basic error handling

Not one mechanism, several, at the points where this pipeline actually breaks in practice:

| Where | What happens | Why |
|---|---|---|
| `run_pipeline.py::execute_kpi_sql` | A failed KPI is retried up to 5 times with the real error fed back to the model. A KPI still failing after that is shown with its full attempt history, not hidden | An LLM's SQL is not guaranteed correct on the first try, most failures are fixable with the right feedback |
| `run_pipeline.py::execute_kpi_sql` | Every field from the AI's JSON response is read with `.get()`, never a bare `kpi["..."]` | An LLM response is never 100% guaranteed to match the exact expected shape, one missing field should not crash the whole run |
| `pipeline/text_quality.py` | If `presidio` fails to import, falls back to a small regex-only PII check (email and phone only) instead of crashing, with a loud printed warning | The PII check should degrade, not disappear silently, if the optional dependency is missing |
| `pipeline/model_kpi_generator.py` | If LangSmith is not configured, the pipeline still runs, untraced, with a printed warning instead of failing | Tracing is for review, not a hard requirement to run the pipeline at all |
| `dashboard/app.py` | If the selected dataset's report file does not exist yet, shows a clear message with the exact command to generate it, instead of a raw file-not-found crash | A user picking the wrong sidebar option, or running the dashboard before the pipeline, should get a next step, not a stack trace |
| `dashboard/app.py` | The ERD only renders when there is something to show (a recommended model with dimensions); when a client's data turns out to be one flat table, the reason no ERD appears is explained instead of showing a blank diagram | Silence looks like a bug even when the underlying result is correct and expected |

None of this is exhaustive production hardening, see `pipeline/pipeline_documentation.md`'s
"Limits compared to a production version" for what is deliberately still out of scope (a second
LLM provider fallback, caching, and so on) and why.

## Repo structure, requirements, and environment

- Repo structure: see `README.md`'s "Repo structure" section.
- `requirements.txt`: pinned at the top level, includes `presidio-analyzer` and
  `presidio-anonymizer` alongside the Round 1 dependencies.
- `.env.example`: documents both required keys (`OPENAI_API_KEY`, `LANGSMITH_API_KEY`) and the
  optional EU data residency endpoint for LangSmith.
