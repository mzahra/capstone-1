# Sector Research

**Sector:** Data & Analytics Consulting Services (B2B, serves clients across sectors)

**Company size:** Small (boutique consultancy, about 10 to 30 people)

## The client: Chleo's company

Chleo runs a small data analytics consultancy. Clients hire the firm to make sense of their
data: reporting, dashboards, "tell us what our numbers mean." Every new client engagement
starts the same way. A raw data export lands on a consultant's desk (CSVs, a database dump, a
warehouse extract). Someone then has to manually:

- figure out what is actually in it, and how clean it is
- work out how the tables relate to each other
- decide what a sensible reporting/data model looks like
- pick the KPIs that matter to that specific client
- write the first draft "here is what your data tells us" report

This is billable, senior consultant time, and it does not scale. Every new client resets the
clock. Chleo has heard "AI" pitched as the fix, but her fear is
that AI is a black box. She does not want to hand judgment calls about a client's data to a
system she cannot explain back to that client.

## Why this sector, why now

- **Market context:** small, independent data and analytics consultancies compete against
  larger firms (Deloitte, Accenture data practices) and also against the trend of clients doing
  more in house with self serve BI tools (Power BI, Looker), which now include their own AI
  copilots (see `opportunities_risks.md` for the competitor landscape). A boutique firm's edge
  is speed and personal attention. Anything that shortens the "new client onboarding" cycle
  helps defend that edge.
- **Client side pressure:** clients increasingly expect a fast first read on their data, in
  days, not weeks, before they commit to a bigger engagement.
- **The transparency angle:** the underlying work (schema profiling, data modeling, KPI
  definition) is standard data pipeline practice. What is new is using an LLM to do a first
  pass and explain its reasoning, which is exactly the transparency story Chleo needs to hear.

## Public data source used for the Round 1 demo

**Olist Brazilian E-Commerce Public Dataset** (Kaggle) is a real multi table relational export
(orders, customers, products, sellers, payments, reviews, geolocation). It stands in for "a new
client's raw data drop." It is used here because it already has real data quality issues
(missing values, duplicates, inconsistent keys), not a clean, staged example. This matches what
a consultant would actually receive from a new client.
