# Use Case Proposals

Company: a small data and analytics consultancy. All three use cases are stages of one
pipeline. A new client's raw data export goes in, and a first draft onboarding report comes
out.

## 1. Automated Data Quality & Schema Profiling

**What it does:** takes a client's raw tables and computes null rates, duplicate rows,
outliers, and candidate primary and foreign keys. Foreign keys are confirmed by checking the
actual values, not just matching column names.

**Why it fits a small consultancy:** this is manual, senior consultant work today, done fresh
for every client. A small firm does not have the people for a dedicated data quality team the
way a large enterprise might. Automating the first pass gives the team more reach, it does not
replace their judgment.

## 2. AI Data Model & KPI Generator

**What it does:** using the schema profile, an LLM proposes a data model (a fact table and its
dimension tables, with a short reason) and a set of business KPIs, along with the SQL to
compute each one. That SQL is then run for real against the data.

**Why it fits a small consultancy:** choosing a data model and picking KPIs is exactly the kind
of judgment call that today takes a senior consultant's time on every client. Running the
generated SQL for real, and showing when it fails instead of hiding it, keeps this a fast draft
for a consultant to check, not an unchecked black box.

## 3. Business Insight & Recommendation Engine

**What it does:** turns the computed KPI values and quality findings into a plain language
report for a non technical client, plus 2 to 3 forward looking data science ideas (for example,
"this data could support demand forecasting") that the firm could offer as follow on work.

**Why it fits a small consultancy:** this is the part the client actually reads. Writing this
first draft by hand is slow. Having the AI draft it, and being able to show the client exactly
how it reasoned through LangSmith, is the direct answer to Chleo's fear that "the AI" cannot be
trusted or explained. It also opens a natural upsell path (the data science ideas) with no
extra consultant effort.
