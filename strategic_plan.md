# Strategic Deployment and Commercialisation Plan

## Phases

### Phase 1: POC (done)

What exists today: the pipeline described in `pipeline/pipeline_documentation.md`, tested end
to end on three structurally different datasets: Olist (clean, relational, about 1.5 million
rows), the full CFPB Consumer Complaint Database (messy, mostly flat, 17.4 million rows), and
Open Food Facts (nested JSON with an inconsistent schema). Includes
the free text PII check, the casing consistency check, and a retry loop that fixes most failed
KPI SQL automatically. This proves the core idea works, not that it is ready for a paying
client's real data unsupervised.

### Phase 2: Pilot

Run the pipeline on 2 to 3 real consultancy clients, next to the existing manual onboarding
process, so the two can be compared directly on time and quality.

**Mandatory gate:** every report goes through a human consultant review before a client ever
sees it. This is not a temporary pilot safeguard to be removed later, it stays a permanent
design requirement, see the "over reliance" risk in `roi_risk_assessment.md` and the Article
50(2) reasoning in `compliance/eu_ai_act_compliance.md`, both of which depend on this step
staying mandatory.

**Hardening work planned for this phase**, carried over from
`pipeline/pipeline_documentation.md`'s limits section:

- Build the per-data-subject search-and-erase capability named as a gap in
  `compliance/gdpr_documentation.md`, needed before real client data (not public stand-in data)
  is used.
- Sign a Data Processing Agreement with each pilot client, and confirm OpenAI's and LangSmith's
  transfer mechanisms against it, per `compliance/gdpr_documentation.md`'s transfers table.
- Security review and one isolated environment per client before any real client data is
  loaded. Costed in `roi_risk_assessment.md`'s "Commercial readiness" table.

### Phase 3: Full deployment

Embedded into Chleo's standard new-client onboarding workflow, not a side experiment. Every new
client gets a Data Copilot first draft as a normal part of onboarding.

**Hardening work planned for this phase:**

- Add caching and basic cost control on repeated runs. Not needed at pilot volume (LLM cost is
  about 0.001 EUR per run, see `roi_risk_assessment.md`), but worth having before full volume.
- Add a fallback to a second LLM provider, so a single vendor's outage or pricing change does
  not block onboarding, see the vendor lock-in risk in `roi_risk_assessment.md`.
- Extend the large-table sampling approach proven in `profiling.py` (see
  `pipeline/pipeline_documentation.md`'s "Data volume" section) to foreign key detection, the
  one piece that was not exercised by the CFPB test since it is a single table.

### Phase 4: Scale (optional)

Licensed as a product to other boutique data consultancies, not just used internally. Discussed
further under Commercialisation model below. This phase only starts if Phase 3's KPIs hold up
across Chleo's own client base first.

**A specific capability this phase depends on, already built and in use, not just planned:**
ingesting a brand-new client's nested JSON without writing a bespoke loader each time, see
`pipeline/load_generic_json.py`. The AI is shown only field names, types, and how often each
appears across the whole source, never a value, and proposes a relational schema, which
deterministic code then applies to every record. This is the actual loader behind the Open Food
Facts report, not a separate demo. Testing found a real reliability gap first, though:
the same prompt against the same data did not always propose the same schema. Mitigated by
asking 3 times and taking the union of tables found, not eliminated. Before Scale can rely on
this without review on a client's data nobody has looked at yet, it needs either a stronger
consistency guarantee or a human review step before a proposed schema is applied, see
`pipeline/pipeline_documentation.md`'s "AI-proposed schema" section for the full finding.

## Timeline and milestones

| Phase | Duration | Milestone that ends it |
|---|---|---|
| POC | Done | Pipeline runs end to end on 3 structurally different datasets, including one at real scale (17.4 million rows) |
| Sprint 1: Discovery | Weeks 1 to 2 | Manual onboarding time and client volume measured, and checked against the break-even table in `roi_risk_assessment.md` ("What has to be true for this to pay off"): **Gate 1**. 2 to 3 pilot clients agreed, "good" defined with them. After the gate: isolated environment, DPA template, consultant training started |
| Sprint 2: Pilot build | Weeks 3 to 4 | Search-and-erase tool in place, security review passed, DPAs signed with every pilot client: **Gate 2** |
| Sprint 3: Pilot run | Weeks 5 to 6 | Pilot clients 1 and 2 onboarded, each with mandatory consultant review. Issues fixed before client 3 |
| Sprint 4: Pilot run and decision | Weeks 7 to 8 | Pilot client 3 onboarded, client feedback collected, AI-assisted vs. manual compared: **Gate 3, go or no-go** |
| Full rollout | Ongoing | Every new client onboarding uses the Data Copilot as standard practice |

Total time to a go or no-go decision: **8 weeks** (four two-week sprints). If a dependency is
late (a pilot client, the lawyer, or the security reviewer), one extra sprint: 10 weeks at most.
Owners, capacity, and the stories behind each sprint are in `delivery_plan.md`.

## Go-to-market

- **Buyers:** boutique data and analytics consultancy owners, roughly 10 to 30 people, the same
  profile as Chleo's own company, per `research/sector_research.md`.
- **Channel:** direct outreach to consultancy owners, plus the data community events and forums
  that boutique firms already use to find tooling and partners. No paid advertising budget
  assumed at this stage.
- **Pricing:** an internal efficiency tool first (Phase 3), not sold externally yet. If Phase 4
  happens, the price has to cover more than the 48 EUR per run. Each licensed consultancy needs
  its own isolated environment (about 8 hours setup, 760 EUR), a processor agreement with us as
  their sub-processor (about 1 hour of lawyer time, 250 EUR), a share of the yearly security
  review, hosting (about 30 EUR per month) and support (about 2 hours, 190 EUR per month). So
  the price floor is a one-time setup fee of about 1,000 EUR plus a monthly subscription of at
  least 220 EUR, before any per-run fee or margin. The numbers come from the same assumptions
  as `cost_estimation/roi_scenarios.py`.
- **Differentiator:** per `research/opportunities_risks.md`'s competitor landscape, no single
  existing tool bundles quality profiling, AI data modeling, and KPI generation for a boutique
  consultancy's specific new-client onboarding workflow. Existing tools assume a client already
  has a warehouse and BI stack in place, this does not.

## Stakeholder communication plan

| Stakeholder | What they need to hear | When |
|---|---|---|
| Chleo (owner) | Pilot results against the manual process, in time and EUR terms | End of each pilot onboarding, and at the go/no-go review |
| Consultants | How to review an AI draft, what to check before sending it to a client, and how to read the LangSmith trace | Before the pilot starts, as a short internal training session |
| Pilot clients | That part of their onboarding is AI-assisted, with a named consultant taking responsibility for the final report | At the start of the engagement, in plain language, not buried in a contract clause |
| Future clients (Phase 3 onward) | The same disclosure, made standard practice, not special-cased for pilot clients only | As part of the standard onboarding kickoff |

## KPIs per phase

| Phase | KPI | Target |
|---|---|---|
| Discovery | Measured manual onboarding time and real client volume | At or above the break-even table in `roi_risk_assessment.md` ("What has to be true for this to pay off"), or the project stops or is rescoped |
| Pilot | Onboarding time, AI-assisted vs. manual | Under 1 hour of consultant time, against the manual time measured in Discovery, per `use_case_definition.md`'s success criteria |
| Pilot | Free text PII correctly flagged before client delivery | 100%, verified against a held-out sample the consultant checks by hand |
| Pilot | Consultant and client view of the report | Rated useful, gathered after each pilot onboarding, not just measured in time saved |
| Pilot to full deployment gate (Gate 3) | All of the above, plus: no pilot report contained unredacted personal data, and the ROI recalculated with the measured numbers is still positive within 36 months | All conditions met, or the gate does not open |
| Full deployment | Share of new-client onboardings using the Data Copilot as standard practice | 100% within 2 months of the go decision |
| Full deployment | ROI | Tracking against the base case in `roi_risk_assessment.md` (-16% at 12 months, 72% at 36 months, break-even after about 15 months), recalculated with the measured pilot numbers |

## Commercialisation model

Two stages, matching Phase 3 and the optional Phase 4:

1. **Internal efficiency tool (Phase 3):** value captured as increased billable consultant
   capacity, not a separate revenue line, per the ROI math in `roi_risk_assessment.md`.
2. **Licensed product (Phase 4, optional):** if Phase 3's KPIs hold, offered to other boutique
   consultancies as a subscription, priced per seat or per onboarding run. This only makes sense
   once the pilot and full deployment phases have proven the tool works reliably on more than
   one firm's own client base, Chleo's, first.
