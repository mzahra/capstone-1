# ROI and Risk Assessment

## ROI

All numbers in this section come from `cost_estimation/roi_scenarios.py`. Change an assumption
there and run it again to get updated tables.

The business case below includes everything a real client deployment needs, not only the
development work. It also shows what happens if the two main assumptions (hours of manual work
replaced, and clients per month) turn out lower than expected.

### One-time investment

**Development (already done).** Blended rate 95 EUR/hour, see
`cost_estimation/cost_analysis.md` for the assumptions.

| Component | Hours | Cost |
|---|---|---|
| Data quality and schema profiling, including the PII and casing checks | 11 | 1,045 EUR |
| AI data model and KPI generation | 10 | 950 EUR |
| Insight generation and dashboard | 6 | 570 EUR |
| LangSmith monitoring and review workflow | 3 | 285 EUR |
| Testing and hardening on three client data types: large data (17.4 million rows, KPI SQL self-correction), and nested JSON (AI-proposed schema) | 17 | 1,615 EUR |
| Compliance, ROI, planning and documentation | 8.5 | 808 EUR |
| **Development total** | **55.5** | **5,273 EUR** |

**Commercial readiness (needed before real client data).** These are estimates, not measured
costs.

| Item | What it covers | Estimate | Cost |
|---|---|---|---|
| Security review | Code and dependency review, secrets handling, check that no raw data leaves the isolated workspace, check of the PII redaction on real-looking data | 16 h x 95 EUR | 1,520 EUR |
| Environment isolation | One separate workspace per client: own database folder, own OpenAI project key, own LangSmith project, encrypted storage, deletion after the engagement ends | 12 h x 95 EUR | 1,140 EUR |
| Processor agreements | Lawyer review of the consultancy's Data Processing Agreement (DPA) template, adding OpenAI and LangSmith as sub-processors, signing their DPAs | 4 h x 250 EUR (lawyer) + 2 h x 95 EUR | 1,190 EUR |
| **Commercial readiness total** | | | **3,850 EUR** |

**Pilot delivery.** The team's time to run the pilot, from the story hours in
`delivery_plan.md`: Discovery, consultant training, the GDPR search-and-erase tool, fixes
between pilot clients, and the final decision.

| Who | Hours | Cost |
|---|---|---|
| Zahra (AI Manager) | 24 | 2,280 EUR |
| Joseph (senior consultant) | 6 | 570 EUR |
| Chleo (owner) | 5 | 475 EUR |
| **Pilot delivery total** | **35** | **3,325 EUR** |

**Total one-time investment: 12,448 EUR** (development 5,273 + commercial readiness 3,850 +
pilot delivery 3,325).

The consultancy already signs a DPA with every client today, because consultants handle client
data manually too. So the DPA work is a one-time template update, not a new cost per client.

### Ongoing costs

**Fixed, per month, whether or not a client is onboarded:**

| Item | Cost |
|---|---|
| Hosting: small EU-hosted virtual machine for the isolated client workspaces | 30 EUR |
| Support and maintenance: dependency updates, model version changes, prompt fixes, bug fixes (2 h) | 190 EUR |
| **Total fixed per month** | **220 EUR (2,640 EUR per year)** |

LangSmith stays on the free tier at this volume (under 5,000 traces per month).

**Per client onboarding run.** The PII and casing checks run locally with Presidio (free, no
API calls). The number of LLM calls is not fixed at 2. Two things can add calls, both seen in
testing:

- A client whose raw data is nested JSON needs 3 extra calls first, to propose the relational
  schema (`load_generic_json.py`'s consensus step). Tabular data skips this.
- Any KPI whose SQL fails adds 1 call per retry, up to 5. Seen on the CFPB run: 2 of 5 KPIs
  needed 1 retry each.

| Item | Cost |
|---|---|
| LLM API calls: 2 calls (model/KPIs, insights), plus 3 if nested JSON, plus 1 per KPI retry | about 0.001 to 0.004 EUR |
| Local PII and casing checks (Presidio, runs locally) | 0 EUR |
| Consultant review (30 minutes, mandatory, before anything reaches the client) | 48 EUR |
| **Total per onboarding run** | **about 48 EUR** |

The LLM figure is measured, not guessed. `pipeline/model_kpi_generator.py` logs the real token
usage OpenAI returns on every call (`cost_summary()`), priced at gpt-4o-mini's rate ($0.15 per
1M input tokens, $0.60 per 1M output tokens). Two real Olist runs cost $0.00133 and $0.00135,
see `outputs/llm_costs.jsonl`.

### Quantified business value

The value is the manual work the tool replaces: profiling, modeling, and the first draft report
for a new client. Today this is an **estimate of 4 to 8 hours** per client (midpoint 6 hours,
570 EUR at 95 EUR/hour). It has not been measured yet. That is the biggest uncertainty in this
whole business case, so the pilot's first sprint (Discovery) measures it first (see "What has to be
true" below).

Two more value sources are real but not counted, because they are hard to put a number on:

- **Risk mitigation:** the PII check catches personal data in free text before a report
  reaches a client, lowering the chance of a GDPR incident. See
  `compliance/gdpr_documentation.md`.
- **Upsell:** the "data science opportunities" suggestions can lead to bigger follow-on
  projects, see `research/use_cases.md`.

### Assumptions table

| Assumption | Base value | Measured or estimated? |
|---|---|---|
| Blended consultant/engineer rate | 95 EUR/hour | Estimated, German market rate |
| Data protection lawyer rate | 250 EUR/hour | Estimated, German market rate |
| Manual onboarding time replaced | 6 hours (range 2 to 8 tested below) | **Estimated, to be measured in the pilot** |
| New client onboardings per month | 2 (range 1 to 2 tested below) | **Estimated, to be checked against the last 12 months of client records** |
| Consultant review per run | 30 minutes | Estimated, to be measured in the pilot |
| LLM cost per run | about 0.001 EUR | Measured |
| PII/casing check cost | 0 EUR | Measured (runs locally) |
| One-time investment paid once, not every year | Yes | |

### ROI at 12 and 36 months

Formula: `ROI = (Net Benefit / Total Cost) x 100`.
Total cost = one-time investment + monthly costs + 48 EUR per run.

**Base case** (6 hours manual work, 2 onboardings per month):

| Period | Value (manual work avoided) | Total cost | Net benefit | ROI |
|---|---|---|---|---|
| 12 months | 570 x 24 = 13,680 EUR | 12,448 + 2,640 + (48 x 24) = 16,240 EUR | -2,560 EUR | **-16%** |
| 36 months | 570 x 72 = 41,040 EUR | 12,448 + 7,920 + (48 x 72) = 23,824 EUR | 17,216 EUR | **72%** |

In the base case, year one does not pay back yet, because of the one-time investment and the
fixed hosting and support costs. The tool pays back after about 15 months, and the return comes
in years two and three.

### Downside cases

| Scenario | Manual hours today | Onboardings per month | ROI 12 months | ROI 36 months | Break-even |
|---|---|---|---|---|---|
| Upside | 8 | 2 | 12% | 130% | about 10 months |
| **Base** | **6** | **2** | **-16%** | **72%** | **about 15 months** |
| Lower volume | 6 | 1 | -56% | -7% | about 41 months |
| Manual work already efficient | 2 | 2 | -72% | -43% | about 16 years, so in practice never |
| Both downsides | 2 | 1 | -85% | -69% | Never |

What this shows:

- **Volume matters.** At 1 onboarding per month the tool pays back after about 3.5 years, just
  outside the 36-month window. About 1.1 onboardings per month is the minimum at 6 hours.
- **Manual time matters more.** If the consultants already do an onboarding in about 2 hours,
  the tool does not pay back at this volume. The saving per run (2 hours minus the 30-minute
  review) is too small to cover the fixed costs.

### What has to be true for this to pay off

Fewest onboardings per month needed to break even within 36 months:

| Manual hours per onboarding today | Onboardings needed per month |
|---|---|
| 2 | 4.0 or more |
| 3 | 2.4 or more |
| 4 | 1.7 or more |
| 6 | 1.1 or more |
| 8 | 0.8 or more |

This turns the two unmeasured assumptions into a clear go/no-go test for the pilot:

1. **Measure the manual baseline** in the Discovery sprint: time-track the next 2 to 3 manual
   onboardings, or reconstruct them from timesheets.
2. **Check the volume** against the last 12 months of client records.
3. **Stop or rescope** if the measured point falls below the table above. For example: 3 hours
   of manual work but only 2 new clients per month means no go. This is Gate 1 in
   `delivery_plan.md`, and it comes before most of the investment is spent. Options then are to reduce the
   fixed costs (for example, support on demand instead of a monthly budget) or to drop the
   project.

### Break-even note

Base case: break-even on the 12,448 EUR one-time investment after about 15 months. Upside case
(8 hours): about 10 months. At 1 onboarding per month: about 41 months.

## Risk matrix

Likelihood and impact are both rated 1 (lowest) to 5 (highest).

| # | Risk | Category | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| 1 | A client's raw export contains sensitive personal data (names, emails, addresses), including inside free text fields | Regulatory | 3 | 5 | A local PII scan (`text_quality.py`) flags and redacts this before anything reaches OpenAI or a report. See `compliance/gdpr_documentation.md` |
| 2 | The PII check misses something, especially on non-English free text (the local model is English-only) or an unusual format | Regulatory | 3 | 4 | The PII check is a first pass, not a guarantee. The mandatory human consultant review before client delivery stays the real control, see `strategic_plan.md` |
| 3 | The LLM recommends a wrong or nonsense data model or KPI, for example a made up column or invalid SQL | Technical | 2 | 3 | The generated SQL is run for real against the schema. A failure is retried up to 5 times, feeding the exact SQL error and the real column names back to the model. A KPI that still fails is shown with its full attempt history, not hidden. Every recommendation is also logged in LangSmith for review |
| 4 | Single LLM provider (OpenAI), no fallback if it has an outage or changes pricing | Technical | 2 | 3 | Documented as a full-deployment hardening item in `pipeline/pipeline_documentation.md`. Add a second provider before scaling past pilot |
| 5 | The pipeline does not generalize well to a client's data shape it has not seen before | Technical | 2 | 3 | Tested directly against three different shapes: Olist (clean relational), CFPB (messy, single flat table, at full scale), and Open Food Facts (genuinely nested JSON, converted into relational tables) |
| 6 | Client data quality issues get smoothed over in the AI written insights, which could mislead the client | Ethical | 3 | 4 | The insight-writing prompt is told to flag it clearly whenever a quality issue affects trust in a number |
| 7 | Over reliance on the AI output replaces the consultant's own judgment entirely | Ethical | 2 | 5 | Positioned as a first draft for a consultant to review, never sent straight to a client. Enforced as a mandatory review gate in the pilot phase, see `strategic_plan.md` |
| 8 | No caching or cost control on repeated runs, cost could grow unexpectedly at higher volume | Operational | 2 | 2 | Cost stays small at the current onboarding volume, see the Ongoing costs section above. Add caching before scaling past pilot volume |
| 9 | The business case assumptions are wrong: manual onboarding is already faster than 4 to 8 hours, or fewer new clients arrive than 2 per month | Business | 3 | 4 | Measure the manual baseline and check client volume in the pilot's Discovery sprint, before more money is spent (Gate 1 in `delivery_plan.md`). Clear stop rule in "What has to be true for this to pay off" above |
| 10 | The technical know-how sits with one person (the AI Manager), so the tool stalls if that person is away or leaves | Operational | 3 | 3 | Setup and run instructions are written (`README.md`, `mvp_documentation.md`). Consultants are trained to run it themselves (P7 in `delivery_plan.md`). The monthly support budget can go to an external developer if needed |
