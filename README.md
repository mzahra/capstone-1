# Data Copilot

Capstone project, Round 1 and Round 2.

**Sector:** Data & Analytics Consulting Services (small company)

**Scenario:** Chleo runs a small data analytics consultancy. Every new client onboarding
starts with a raw data export. Then hours of manual profiling, modeling, and KPI selection
follow. This work does not scale. Chleo is also worried she cannot hand this work to "the AI"
without being able to explain what it did, or trust it with data that might contain personal
information.

**What this is:** a small Python pipeline. It takes a raw client export and produces, end to
end: a data quality and schema profile (including a check for personal data hidden in free
text), an AI recommended data model, a set of business KPIs (computed for real, not just
proposed, with failed KPI SQL automatically retried against the AI), a plain language insight
report, and a few forward looking data science suggestions. Every AI decision is logged in
LangSmith so it can be reviewed, not treated as a black box.

Demoed with three datasets, standing in for three different "new client" raw exports, each
testing a different data shape:

- **Olist Brazilian E-Commerce**: clean, relational, about 1.5 million rows.
- **CFPB Consumer Complaint Database**: messy, mostly one flat table, free-text heavy, and
  tested at its full real size, 17.4 million rows, to check the pipeline holds up past one tidy
  demo dataset. See `pipeline/pipeline_documentation.md`'s "Data volume" section for how.
- **Open Food Facts**: genuinely semi-structured JSON, where even the top-level fields are not
  consistent record to record, converted into relational tables (`products`, `ingredients`,
  `categories`, `nutriments`) by `pipeline/load_openfoodfacts_data.py`. See
  `pipeline/pipeline_documentation.md`'s "Data structure" section for how.

## Setup

```bash
conda activate myenv
pip install -r requirements.txt
python -m spacy download en_core_web_sm   # one-time, needed for the free-text PII check
cp .env.example .env   # fill in OPENAI_API_KEY and LANGSMITH_API_KEY
```

Olist needs a manual download: get the dataset from Kaggle ("Brazilian E-Commerce Public
Dataset by Olist") and place the CSV files in `data/`. CFPB and Open Food Facts do not,
`pipeline/load_cfpb_data.py` and `pipeline/load_openfoodfacts_data.py` both download their own
public data automatically.

## Run it

```bash
# Olist
python pipeline/load_data.py      # loads CSVs into data/warehouse.db
python pipeline/run_pipeline.py   # runs the full pipeline, writes outputs/report.json

# CFPB (downloads and loads the full 17.4 million row dataset, takes about 15-30 minutes)
python pipeline/load_cfpb_data.py
python pipeline/run_pipeline.py --db data/warehouse_cfpb.db --out outputs/report_cfpb.json

# Open Food Facts (streams a 25,000 product slice from a 12.8 GB source, a few minutes)
python pipeline/load_openfoodfacts_data.py
python pipeline/run_pipeline.py --db data/warehouse_openfoodfacts.db --out outputs/report_openfoodfacts.json

# any of the above
streamlit run dashboard/app.py    # pick the client dataset from the sidebar dropdown
```

## What is in outputs/

These files are already included in the repo, so the dashboard works right away without
needing to run the pipeline first (which needs your own OpenAI and LangSmith API keys).

- **`profiling*.json`** (one per dataset): the raw data quality and schema profile,
  produced by `pipeline/profiling.py`. Per table and column stats (nulls, duplicates, outliers,
  detected PII, casing consistency), primary key candidates, and confirmed foreign key
  relationships. Feeds the "Checks performed" table in the dashboard's technical details. Large
  tables (over 100,000 rows) are sampled for these stats rather than loaded whole, row counts
  and KPI results stay exact either way, see `pipeline/pipeline_documentation.md`.
- **`report*.json`** (one per dataset): the full pipeline output, produced by
  `pipeline/run_pipeline.py`. Combines the profile summary with the AI recommended data model,
  the KPI list with real executed results, the quality findings, the data science
  opportunities, and the AI written business insights. This is the main file `dashboard/app.py`
  reads to render the report.
- **`Client Onboarding Report.pdf`**: a static snapshot of the Round 1 dashboard, so the report
  can be viewed without running Streamlit at all.

## Repo structure

```
research/            sector research, opportunity and risk mapping, use cases, competitor notes
dashboard/           Streamlit dashboard (app.py) and its documentation
pipeline/            the pipeline: load data, profile it, AI model/KPI/insight generation, orchestration
langsmith/            monitoring setup and what is traced, and why
cost_estimation/      upfront cost and timeline estimate, with assumptions
compliance/           EU AI Act and GDPR documentation
feedback/             round1_decision.md, written after presenting to teaching staff
outputs/              generated reports and profiles, for all three datasets
```

