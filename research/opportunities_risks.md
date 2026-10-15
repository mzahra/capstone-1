# Opportunities & Risks

## Opportunities

| Opportunity                   | Description                                                                                                                                                | Why it matters to Chleo                                     |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Faster client onboarding      | Automate the first pass profiling, modeling, KPI, and insight cycle that today takes a senior consultant an estimated 4 to 8 hours per new client          | Directly increases billable capacity without hiring         |
| Consistency                   | Every client gets the same careful quality and schema check, not just what a given consultant happens to remember                                          | Reduces "it depends who did it" quality gaps                |
| A sellable transparency story | Every AI step (model choice, KPI choice, insight wording) is logged and can be explained. Chleo can show a client exactly why the AI concluded what it did | Answers her core fear directly, the opposite of a black box |
| Upsell surface                | The "data science opportunities" suggestions (churn prediction, forecasting, and so on) are a natural lead in to bigger follow on projects                 | New revenue line from a step that already happens           |

## Risks

| Risk                                                                                                                      | Likelihood    | Impact            | Mitigation                                                                                                                                                                                                 |
| ------------------------------------------------------------------------------------------------------------------------- | ------------- | ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| LLM recommends a wrong or nonsense data model or KPI (a made up column, invalid SQL)                                      | Medium        | Medium            | Run the generated SQL against the real schema and show failures instead of hiding them (see`dashboard/app.py`). The LangSmith trace lets a consultant check every recommendation before a client sees it |
| Client data quality issues get smoothed over in the AI written insights, which could mislead the client                   | Medium        | High              | The insight writing prompt is told to flag it clearly whenever a quality issue affects trust in a number                                                                                                   |
| Over reliance replaces consultant judgment completely                                                                     | Low to Medium | High              | Positioned as a first draft for a consultant to review, not an output sent straight to a client (see`strategic_plan.md`)                                                                                 |
| Client data includes sensitive personal information (names, emails, addresses)                                            | Medium        | High (compliance) | Only public data is used in testing. Real client work needs per client data agreements and data minimization, covered in`compliance/gdpr_documentation.md`                                               |
| Generalization risk: a pipeline tuned on one client's schema may not work as well on a very different sector's data shape | Medium        | Medium            | Tested on three differently shaped datasets: clean relational, messy flat at 17.4 million rows, and nested JSON                                                                                            |

## Competitor Landscape

None of the pieces here are brand new on their own. But no single tool bundles them for a small
consultancy's client onboarding workflow. By category:

- **Data quality and observability** (mature): Great Expectations, dbt tests, Monte Carlo,
  Soda, Anomalo, Bigeye. These are built for enterprise teams that already have a data team and a warehouse.
- **Schema and catalog with lineage** (mature): dbt docs, DataHub, Atlan, OpenMetadata. These document what already exists, but they do not recommend a data model design.
- **KPI and semantic layers** (mature): dbt Semantic Layer, Cube, LookML. A human still has to define the metrics. The layer does not propose KPIs on its own.
- **Auto insight, sometimes called "augmented analytics"** (an older category, now getting LLM narration added): Power BI Quick Insights and Copilot, Tableau Explain Data and Pulse, Qlik Insight Advisor, ThoughtSpot Spotter, Databricks Genie, Snowflake Cortex Analyst.
- **LLM driven data model recommendation** is the least common piece. A few "AI data engineer" startups are exploring it, but it is not yet a mainstream, off the shelf product.

**The pitch to Chleo:** each piece already exists somewhere, but usually inside a big tool that
assumes a client already has a warehouse and a BI stack in place. The value here is one small, integrated pipeline built for a boutique consultancy that has to onboard a new client fast, before that bigger tooling investment exists.
