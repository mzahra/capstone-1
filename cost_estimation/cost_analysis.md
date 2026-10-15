# Cost Estimate

## Assumptions

- Market: Germany. Blended consultant or engineer rate: **95 EUR/hr**, a typical freelance/
  small-consultancy data engineering rate in Germany.
- Data protection lawyer rate: **250 EUR/hr**, a typical German market rate.
- LLM cost: OpenAI `gpt-4o-mini`. Measured, not estimated: `pipeline/model_kpi_generator.py`'s
  `cost_summary()` logs OpenAI's own token usage on every call. About 0.001 EUR per run, see
  `outputs/llm_costs.jsonl`.
- LangSmith: the free tier is enough at this volume (under 5,000 traces per month).

## Development cost (one time, already done)

| Component | Hours | Cost |
|---|---|---|
| Data quality and schema profiling, including the PII and casing checks | 11 | 1,045 EUR |
| AI data model and KPI generation | 10 | 950 EUR |
| Insight generation and dashboard | 6 | 570 EUR |
| LangSmith monitoring and review workflow | 3 | 285 EUR |
| Testing and hardening on three client data types | 17 | 1,615 EUR |
| Compliance, ROI, planning and documentation | 8.5 | 808 EUR |
| **Total development** | **55.5** | **5,273 EUR** |

## Commercial readiness (one time, before real client data)

| Item | Estimate | Cost |
|---|---|---|
| Security review | 16 h x 95 EUR | 1,520 EUR |
| One isolated environment per client | 12 h x 95 EUR | 1,140 EUR |
| Processor agreements (DPA template review, OpenAI and LangSmith as sub-processors) | 4 h x 250 EUR + 2 h x 95 EUR | 1,190 EUR |
| **Total commercial readiness** | | **3,850 EUR** |

## Pilot delivery (one time)

The team's time to run the pilot, from the story hours in `delivery_plan.md`.

| Who | Hours | Cost |
|---|---|---|
| Zahra (AI Manager) | 24 | 2,280 EUR |
| Joseph (senior consultant) | 6 | 570 EUR |
| Chleo (owner) | 5 | 475 EUR |
| **Total pilot delivery** | **35** | **3,325 EUR** |

**Total one-time investment: 12,448 EUR.**

## Ongoing cost

| Item | Cost |
|---|---|
| Hosting (small EU-hosted virtual machine) | 30 EUR per month |
| Support and maintenance (2 h) | 190 EUR per month |
| LLM API calls | about 0.001 EUR per onboarding |
| Consultant review (30 minutes, mandatory, before the report reaches the client) | 48 EUR per onboarding |

A consultant currently spends an estimated 4 to 8 hours per new client on profiling, modeling,
and the first draft report. That is about 380 to 760 EUR in labor. The full ROI, including the
downside cases (less manual work to replace, fewer clients), is in `roi_risk_assessment.md`,
calculated by `roi_scenarios.py` in this folder.
