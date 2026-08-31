# Capstone Round 1: Data Copilot

**Sector:** Data & Analytics Consulting Services (small company)

**Scenario:** Chleo runs a small data analytics consultancy. Every new client onboarding
starts with a raw data export. Then hours of manual profiling, modeling, and KPI selection
follow. This work does not scale. Chleo is also worried she cannot hand this work to "the AI"
without being able to explain what it did.

**What this is:** a small Python pipeline. It takes a raw multi table client export and
produces, end to end: a data quality and schema profile, an AI recommended data model, a set
of business KPIs (computed for real, not just proposed), a plain language insight report, and
a few forward looking data science suggestions. Every AI decision is logged in LangSmith so it
can be reviewed, not treated as a black box.

Demoed with the **Olist Brazilian E-Commerce** dataset, used here as a stand in for "a new
client's raw export."

## Setup

```bash
conda activate myenv
pip install -r requirements.txt
cp .env.example .env   # fill in OPENAI_API_KEY and LANGSMITH_API_KEY
```

Download the Olist dataset from Kaggle ("Brazilian E-Commerce Public Dataset by Olist") and
place the CSV files in `data/`.

## Run it

```bash
python pipeline/load_data.py      # loads CSVs into data/warehouse.db
python pipeline/run_pipeline.py   # runs the full pipeline, writes outputs/report.json
streamlit run dashboard/app.py    # view the client onboarding report
```

## What is in outputs/

These files are already included in the repo, so the dashboard works right away without
needing to run the pipeline first (which needs your own OpenAI and LangSmith API keys).

- **`profiling.json`**: the raw data quality and schema profile, produced by
  `pipeline/profiling.py`. Per table and column stats (nulls, duplicates, outliers), primary
  key candidates, and confirmed foreign key relationships. Feeds the "Checks performed" table
  and the ER diagram in the dashboard's technical details.
- **`report.json`**: the full pipeline output, produced by `pipeline/run_pipeline.py`. Combines
  the profile summary with the AI recommended data model, the KPI list with real executed
  results, the quality findings, the data science opportunities, and the AI written business
  insights. This is the main file `dashboard/app.py` reads to render the report.
- **`Client Onboarding Report.pdf`**: a static snapshot of the dashboard, so the report can be
  viewed without running Streamlit at all.

## Repo structure

```
research/            sector research, opportunity and risk mapping, use cases, competitor notes
dashboard/           Streamlit dashboard (app.py) and its documentation
pipeline/             the POC: load data, profile it, AI model/KPI/insight generation, orchestration
langsmith/            monitoring setup and what is traced, and why
cost_estimation/      upfront cost and timeline estimate, with assumptions
feedback/             round1_decision.md, written after presenting to teaching staff
```

## Status

This is the Round 1 build. See `feedback/round1_decision.md` (added after the presentation)
for whether Round 2 keeps this industry and use case, or changes direction.
