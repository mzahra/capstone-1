# ROI and Risk Assessment

## ROI

### Upfront costs

Two build phases so far, both at a blended rate of 95 EUR/hour (see
`cost_estimation/cost_analysis.md` for the Round 1 breakdown and its assumptions). Round 2's
hours are broken out below rather than given as one number, since the actual scope grew
substantially past the first estimate, three datasets tested at real scale, not one slice, plus a SQL self-correction loop.

| Phase | Hours | Cost |
|---|---|---|
| Round 1: profiling, model/KPI generation, insights, LangSmith, one dataset | 32 | 3,040 EUR |
| Round 2: free text quality + PII + casing checks | 3 | 285 EUR |
| Round 2: CFPB at full scale (streaming loader, large-table sampling rework, KPI SQL retry loop) | 6 | 570 EUR |
| Round 2: Open Food Facts (AI-driven schema inference, consensus mechanism, and about 9 real bugs found and fixed along the way) | 6 | 570 EUR |
| Round 2: compliance docs, ROI/risk, strategic plan, delivery plan, doc maintenance | 8 | 760 EUR |
| Round 2: MVP documentation | 0.5 | 48 EUR |
| **Total upfront cost so far** | **55.5** | **5,273 EUR** |

Not yet included: the no-code/low-code POC and the final presentation, both still open per
`delivery_plan.md`'s Definition of done. This table will need one more update once those are
done.

### Ongoing costs

Per client onboarding run. The new Round 2 PII and casing checks run locally with Presidio
(free, no API calls), so they add no marginal cost. The LLM call count is not fixed at 2 like
in Round 1, two things can add more calls, both real and already seen in testing:

- A client whose raw data is nested JSON, not already a table, needs 3 extra calls first, to
  propose the relational schema (`load_generic_json.py`'s consensus step, asks the AI 3 times
  and takes the union). A client whose data is already tabular skips this step entirely.
- Any KPI whose SQL fails adds 1 more call per retry, up to 5. Seen for real on the CFPB run:
  2 of 5 KPIs needed 1 retry each.

| Item | Cost |
|---|---|
| LLM API calls: 2 calls (model/KPIs, insights), plus 3 more if the client's data is nested JSON, plus 1 per KPI retry | about 0.001 to 0.004 EUR |
| Local PII and casing checks (Presidio, runs on the consultant's machine) | 0 EUR |
| Consultant review time (30 minutes, checking the AI's draft before it reaches the client) | 48 EUR |
| **Total per onboarding run** | **about 48 EUR** |

The EUR figure above is not a guess: `pipeline/model_kpi_generator.py` now logs the real token
usage OpenAI returns on every call (`cost_summary()`), prices it at gpt-4o-mini's real rate
($0.15 per 1M input tokens, $0.60 per 1M output tokens), and every `report_*.json` carries the
exact figure for that run under `"cost"`. A real Olist run: 2 calls, 6,411 tokens, $0.001361
(about 0.0012 EUR). The LLM cost barely moves the total either way, it stays small next to the
48 EUR review time regardless of data shape or retries.

### Quantified business value

A consultant currently spends an estimated 4 to 8 hours per new client on profiling, modeling,
and the first draft report. At 95 EUR/hour, that is 380 to 760 EUR of labor per client, midpoint
about 570 EUR. Against the Data Copilot's 48 EUR cost per run (including the human review step),
that is a net saving of about 332 to 712 EUR per onboarding, midpoint about 522 EUR.

Two more value sources are real but not counted in the ROI math below, since they are harder to
put a reliable number on:

- **Risk mitigation value:** the Round 2 PII check catches personal data hidden in free text
  before a report reaches a client, lowering the chance of a GDPR incident. See
  `compliance/gdpr_documentation.md`.
- **Upsell value:** the "data science opportunities" suggestions are a lead-in to bigger follow
  on projects for the consultancy, see `research/use_cases.md`.

### Assumptions table

| Assumption | Value |
|---|---|
| Blended consultant/engineer rate | 95 EUR/hour |
| Manual onboarding time avoided per client | 4 to 8 hours (midpoint 6) |
| New client onboardings per month | 2 (24 per year) |
| LLM model | OpenAI gpt-4o-mini |
| PII/casing check compute cost | 0 EUR (runs locally) |
| Upfront cost is a one-time cost, paid once, not repeated each year | Yes |

### ROI for 12 and 36 months

Using `ROI = (Net Benefit / Total Cost) x 100`, with 24 onboardings per year and the 570 EUR
midpoint manual cost per onboarding as the value avoided:

| Period | Gross value avoided | Total cost (upfront + ongoing) | Net benefit | ROI |
|---|---|---|---|---|
| 12 months | 570 x 24 = 13,680 EUR | 5,273 + (48 x 24) = 6,425 EUR | 7,255 EUR | **113%** |
| 36 months | 570 x 24 x 3 = 41,040 EUR | 5,273 + (48 x 24 x 3) = 8,729 EUR | 32,311 EUR | **370%** |

The upfront cost is only paid once, in year one, so ROI grows faster after that, since only the
48 EUR per run ongoing cost keeps accumulating against a fixed one-time investment.

### Break-even note

At the 522 EUR midpoint net saving per run, break-even on the 5,273 EUR upfront cost is about 10
onboarding runs, or about 5 months at 2 clients a month. Using the wider 332 to 712 EUR range
instead, break-even falls between 8 months (slow case, 332 EUR/run) and 4 months (fast case,
712 EUR/run).

## Risk matrix

Likelihood and impact are both rated 1 (lowest) to 5 (highest).

| # | Risk | Category | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| 1 | A client's raw export contains sensitive personal data (names, emails, addresses), including inside free text fields | Regulatory | 3 | 5 | Round 2's local PII scan (`text_quality.py`) flags and redacts this before anything reaches OpenAI or a report. See `compliance/gdpr_documentation.md` |
| 2 | The PII check misses something, especially on non-English free text (the local model is English-only) or an unusual format | Regulatory | 3 | 4 | The PII check is a first pass, not a guarantee. The mandatory human consultant review before client delivery stays the real control, see `strategic_plan.md` |
| 3 | The LLM recommends a wrong or nonsense data model or KPI, for example a made up column or invalid SQL | Technical | 2 | 3 | The generated SQL is run for real against the schema. A failure is retried up to 5 times, feeding the exact SQL error and the real column names back to the model. A KPI that still fails is shown with its full attempt history, not hidden. Every recommendation is also logged in LangSmith for review |
| 4 | Single LLM provider (OpenAI), no fallback if it has an outage or changes pricing | Technical | 2 | 3 | Documented as a full-deployment hardening item in `pipeline/pipeline_documentation.md`. Add a second provider before scaling past pilot |
| 5 | The pipeline does not generalize well to a client's data shape it has not seen before | Technical | 2 | 3 | Round 2 tests this directly against three different shapes: Olist (clean relational), CFPB (messy, single flat table, at full scale), and Open Food Facts (genuinely nested JSON, converted into relational tables). Also found and fixed a real gap along the way: foreign key detection required an exact column name match, and missed Open Food Facts' real relationships until that was broadened |
| 6 | Client data quality issues get smoothed over in the AI written insights, which could mislead the client | Ethical | 3 | 4 | The insight-writing prompt is told to flag it clearly whenever a quality issue affects trust in a number |
| 7 | Over reliance on the AI output replaces the consultant's own judgment entirely | Ethical | 2 | 5 | Positioned as a first draft for a consultant to review, never sent straight to a client. Enforced as a mandatory review gate in the pilot phase, see `strategic_plan.md` |
| 8 | No caching or cost control on repeated runs, cost could grow unexpectedly at higher volume | Operational | 2 | 2 | Cost stays small at the current onboarding volume, see the Ongoing costs section above. Add caching before scaling past pilot volume |
