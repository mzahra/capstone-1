# Dashboard Documentation

**Tool:** Python (Streamlit and Plotly) instead of PowerBI. This keeps the whole pipeline in
one language and one stack for a 1 day build. It also fits better since the dashboard content
changes based on what the AI recommends for each client, which does not fit a hand built .pbix
file well.

**Run it:**
```
python pipeline/load_data.py      # loads Olist CSVs into data/warehouse.db
python pipeline/run_pipeline.py   # profiles data, calls the AI, writes outputs/report.json
streamlit run dashboard/app.py    # view the report
```

## Sections and why they are there

| Section | Metrics/content | Why a CEO or ops lead would care |
|---|---|---|
| KPIs | 5 to 7 metrics from the AI generated, executed SQL (for example total revenue, average order value, delivery time, review score, repeat customer rate) | These are the numbers a client opens the report to see |
| Recommended data model | Fact and dimension diagram, with the reasoning | Shows the AI's reasoning, not just its answer. This is the transparency layer |
| Data quality findings | Plain language issues found during profiling | A client needs to know how much to trust the KPIs above |
| Business insights | AI written plain language summary of what the KPIs mean | The actual deliverable a non technical client reads |
| Data science opportunities | 2 to 3 forward looking suggestions | An upsell surface, explained in `research/use_cases.md` |

Failed KPIs (where the AI generated SQL did not run cleanly) are shown, not hidden. This is an
honest choice. A consultant reviewing this draft needs to see where the AI got it wrong.
