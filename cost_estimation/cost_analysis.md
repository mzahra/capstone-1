# Cost Estimate, Round 1 (Upfront, Pilot Scale)

## Assumptions

- Market: Germany. Blended consultant or engineer rate: **95 EUR/hr**, a typical freelance/
  small-consultancy data engineering rate in Germany
- Build scope: the pipeline as demoed (quality and schema profiling, model and KPI generation,
  insight generation, LangSmith monitoring, one client dataset), not a full multi client product
- LLM cost: OpenAI `gpt-4o-mini`, about 2 calls per client onboarding run. This was a rough
  guess at the time; Round 2 added real cost tracking to the pipeline itself
  (`pipeline/model_kpi_generator.py`'s `cost_summary()`, logging OpenAI's own token usage on
  every call) and found about 0.001 EUR per run, see `roi_risk_assessment.md`'s Ongoing costs
  section. Small compared to labor cost either way.
- LangSmith: the free tier is enough at pilot volume (under 5,000 traces per month)

Note: the 32 hours below is not the same as the roughly 8 hours the Round 1 demo itself took
(see `timeline_estimate.md`). The demo proved the concept works on one dataset. The 32 hours
is the estimate to harden it into something a consultancy would actually put in front of a
paying client: testing against more than one dataset, more rigorous prompt checks, and a real
human review workflow before a report ever reaches a client.

## Upfront build cost (one time)

| Item | Hours | Cost |
|---|---|---|
| Profiling and quality check pipeline | 8 | 760 EUR |
| Model and KPI generation (prompt design, structured output, checks) | 10 | 950 EUR |
| Insight generation and dashboard | 6 | 570 EUR |
| LangSmith integration and review workflow | 3 | 285 EUR |
| Testing against 1 to 2 real, client like datasets | 5 | 475 EUR |
| **Total build** | **32** | **3,040 EUR** |

## Ongoing cost (per client onboarding run)

| Item | Cost |
|---|---|
| LLM API calls | about 0.001 EUR (see `roi_risk_assessment.md` for the real measured figure) |
| Consultant review time (30 minutes, a quick check of the AI's draft before it reaches the client) | 48 EUR |
| **Total per onboarding** | **about 48 EUR** |

A consultant currently spends an estimated 4 to 8 hours per
new client on profiling, modeling, and the first draft report. That is about 380 to 760 EUR in
labor. Even with a 30 minute human review step, this is a large drop in per client onboarding
cost, once the one time build cost is paid back. See the full ROI math in Round 2's
`roi_risk_assessment.md`.
