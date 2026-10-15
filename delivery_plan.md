# Delivery Plan

## The AI Manager's role in this project

The technical files in this repo (the pipeline, the compliance docs, the ROI numbers) are what an AI Manager is responsible for getting right. This file is the other half of the role: turning a business problem into small pieces of work, giving each piece an owner, planning it against real team capacity, and making the go/no-go decisions visible.

It has two parts:

1. **Build (done):** the work that produced the current Data Copilot, split into small stories
   and mapped to two-week sprints.
2. **Pilot (next):** the plan to take it from tested-on-public-data to used-on-real-clients,
   in four two-week sprints, with three decision gates.

## Team and capacity

| Person                     | Role                                                               | Capacity                                         |
| -------------------------- | ------------------------------------------------------------------ | ------------------------------------------------ |
| Chleo                      | Owner of the consultancy, sponsor, makes the go/no-go decisions    | About 2 hours per sprint, plus the sprint review |
| Zahra                      | AI Manager: plans and builds the solution, owns delivery           | 20 hours per week (40 per sprint), part time     |
| Joseph                     | Senior consultant, pilot lead: runs and reviews the client reports | About 8 hours per sprint, next to client work    |
| External lawyer            | Reviews the Data Processing Agreement (DPA) template               | 4 hours, one time                                |
| External security reviewer | Reviews the solution before real client data is loaded             | 16 hours, one time, booked by Zahra              |
| 2 to 3 pilot clients       | Provide real data, agree to AI-assisted onboarding, give feedback  | Not planned by us. A dependency, see below       |

Sprint length is two weeks. Every sprint ends with a short review with Chleo: what was done,
what was not, and why.

How to read the story tables: the story ("As Chleo, I want...") names the stakeholder who needs
the result. The **Owner** is the person who does the work and delivers it. They are often not
the same person. For example, Chleo needs the real manual onboarding time (P1) to make her
investment decision, but Joseph measures it, because he does the onboardings.

## Part 1: Build (done)

All stories owned by Zahra, accepted by Chleo. Hours are estimated effort (not timed), and
match the development cost in `cost_estimation/cost_analysis.md` (55.5 hours, 5,273 EUR).

### Build sprint 1: a working first draft on one client's data (30 hours)

| #  | Story                                                                                                                                                                   | Hours | Depends on | Status |
| -- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- | ---------- | ------ |
| B1 | As a consultant, I want a data quality profile of a new client's export (missing values, duplicates, outliers, how tables connect) in minutes, so I don't do it by hand | 8     |            | Done   |
| B2 | As a consultant, I want personal data in free text flagged and removed before anything leaves my machine, so I never expose a client's customers                        | 3     | B1         | Done   |
| B3 | As a consultant, I want a proposed data model for the client's data, so I don't design it from zero                                                                     | 5     | B1         | Done   |
| B4 | As a consultant, I want a KPI list whose numbers are actually calculated on the client's data, not just suggested, so I can trust them                                  | 5     | B3         | Done   |
| B5 | As Chleo, I want a plain-language report and dashboard for the client, so the first meeting starts with results                                                         | 6     | B4         | Done   |
| B6 | As Chleo, I want every AI decision logged and reviewable, so I can explain to a client what the AI did                                                                  | 3     | B3         | Done   |

### Build sprint 2: proof it works on different clients, and is allowed to (25.5 hours)

| #   | Story                                                                                                                                   | Hours | Depends on | Status |
| --- | --------------------------------------------------------------------------------------------------------------------------------------- | ----- | ---------- | ------ |
| B7  | As Chleo, I want the tool to handle a very large client export (17.4 million rows) without crashing, so a big client is not a problem   | 4     | B1         | Done   |
| B8  | As a consultant, I want a KPI calculation that fails to be corrected automatically, so I don't fix basic AI mistakes by hand            | 2     | B4         | Done   |
| B9  | As Chleo, I want a client's nested JSON data loaded without writing new code, so a new data format is not a new engineering project     | 6     | B1         | Done   |
| B10 | As Chleo, I want the full flow tested on three different kinds of client data, so I know it is not tuned to one demo                    | 5     | B7, B8, B9 | Done   |
| B11 | As Chleo, I want to know the tool is legal under the EU AI Act and GDPR before real client data touches it, so I don't create liability | 3     | B2         | Done   |
| B12 | As Chleo, I want the cost, return, and risks in numbers, so I can decide whether to invest                                              | 2.5   | B10        | Done   |
| B13 | As Chleo, I want a rollout plan with owners and decision gates, so I know what happens next and who does it                             | 2     | B12        | Done   |
| B14 | As a consultant, I want setup and run instructions, so I can run it myself without the builder                                          | 1     | B10        | Done   |

## Part 2: Pilot (next)

Goal: run the Data Copilot on 2 to 3 real client onboardings, next to the normal manual
process, and decide with real numbers whether to roll it out.

Total: four two-week sprints, 8 weeks, the same timeline as `strategic_plan.md`. If a
dependency is late (see Dependencies below), one extra sprint: 10 weeks at most.

### Sprint 1: is it worth it? (Discovery)

| #  | Story                                                                                                                                                                              | Owner                           | Hours        | Depends on |
| -- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- | ------------ | ---------- |
| P1 | As Chleo, I want the real time of the last 3 manual onboardings measured, so the business case uses real numbers, not an estimate                                                  | Joseph                          | 3            |            |
| P2 | As Chleo, I want the number of new clients in the last 12 months counted, so I know the real volume                                                                                | Chleo                           | 1            |            |
| P3 | As Chleo, I want P1 and P2 checked against the break-even table ("What has to be true for this to pay off" in`roi_risk_assessment.md`), so we stop early if it will not pay back | Zahra                           | 2            | P1, P2     |
| P4 | As a pilot client, I want to hear in plain language that part of my onboarding is AI-assisted and checked by a named consultant, so I can agree with confidence                    | Chleo                           | 2            | P3         |
| P5 | As a pilot client, I want my own data stored separately, encrypted, and deleted after the project, so it never mixes with other clients' data                                      | Zahra                           | 12           | P3         |
| P6 | As Chleo, I want the DPA template updated (OpenAI and LangSmith added as sub-processors) and reviewed by a lawyer, so we are allowed to process client data with these tools       | Zahra, with the external lawyer | 2 + 4 lawyer | P3         |
| P7 | As a consultant, I want a short training on how to review the AI draft and what to check, so every review is done the same way                                                     | Zahra                           | 4            | P3         |
| P8 | As a pilot client, I want "a good result" agreed with me up front, so the pilot is judged on what matters to me                                                                    | Joseph                          | 2            | P4         |

**Capacity check:** Zahra 20 of 40 hours, Joseph 5 of 8, Chleo 3 of 2 (one hour over, accepted because this sprint holds her biggest decision).

**Gate 1, end of Discovery (P3):** if the measured manual time and client volume are below the break-even table in `roi_risk_assessment.md` ("What has to be true for this to pay off"), the pilot stops here. Cost at that point: only the Discovery hours, not the full investment. P4 to P8 start only after this gate passes. The lawyer and the security reviewer are booked in week 1, but not paid until their work starts.

### Sprint 2: safe for real client data (Pilot build)

| #   | Story                                                                                                                         | Owner                             | Hours                | Depends on |
| --- | ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | -------------------- | ---------- |
| P9  | As a person in a client's data, I want the consultancy to find and delete my data on request, so my GDPR rights are respected | Zahra                             | 8                    | P5         |
| P10 | As Chleo, I want an independent security review before real client data is loaded, so I know there is no obvious hole         | Zahra, with the external reviewer | 16 external reviewer | P5, P9     |
| P11 | As a pilot client, I want a signed DPA before I share data, so my data is legally protected                                   | Chleo                             | 1                    | P4, P6     |

**Capacity check:** Zahra 8 of 40 hours. The rest is kept free on purpose: fixing whatever the
security review finds has to fit in this sprint, or Gate 2 slips. Chleo 1 of 2.

**Gate 2, security (P10):** no real client data is loaded until the review has no open
high-risk findings and every pilot client has a signed DPA (P11).

### Sprint 3: first real clients (Pilot run)

| #   | Story                                                                                                                                            | Owner  | Hours                         | Depends on   |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------ | ----------------------------- | ------------ |
| P12 | As a consultant, I want the AI first draft for pilot clients 1 and 2 within one day of receiving their data, so I start the real analysis sooner | Joseph | 2 x 0.5 review, plus run time | P7, P10, P11 |
| P13 | As Chleo, I want the time of each AI-assisted onboarding logged next to the manual one, so the comparison is fair                                | Joseph | Part of P12                   | P12          |
| P14 | As a consultant, I want problems found with client 1 fixed before client 2, so the same issue does not happen twice                              | Zahra  | 6 (buffer)                    | P12          |

**Capacity check:** Zahra 6 of 40 hours, Joseph about 2 of 8 plus his normal manual onboarding work for the same clients.

### Sprint 4: the decision (Pilot run and review)

| #   | Story                                                                                                                                                               | Owner  | Hours                     | Depends on    |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ------------------------- | ------------- |
| P15 | As a consultant, I want the AI first draft for pilot client 3, so the decision rests on more than two cases                                                         | Joseph | 0.5 review, plus run time | P14           |
| P16 | As a pilot client, I want to be asked what I thought of the report, so my view counts in the decision                                                               | Joseph | 1                         | P12, P15      |
| P17 | As Chleo, I want one page comparing AI-assisted and manual onboarding (time, quality, client feedback, ROI recalculated with the measured numbers), so I can decide | Zahra  | 4                         | P13, P15, P16 |
| P18 | As Chleo, I want a go/no-go meeting with a clear recommendation, so the decision is made, not postponed                                                             | Chleo  | 1                         | P17           |

**Capacity check:** Zahra 4 of 40 hours, Joseph about 1.5 of 8, Chleo 1 of 2.

**Gate 3, go/no-go (P18):** roll out only if all of these hold:

- AI-assisted onboarding is under 1 hour of consultant time, against the measured manual time
- No pilot report contained unredacted personal data
- Consultants and pilot clients rate the report as useful
- The ROI, recalculated with the measured numbers, is still positive within 36 months

## Pilot effort and cost

| Who                                                                                  | Hours        | Covered in                                      |
| ------------------------------------------------------------------------------------ | ------------ | ----------------------------------------------- |
| Zahra: environment isolation (P5)                                                    | 12           | Commercial readiness,`roi_risk_assessment.md` |
| Zahra and lawyer: DPA template (P6)                                                  | 2 + 4 lawyer | Commercial readiness                            |
| External reviewer: security review (P10)                                             | 16           | Commercial readiness                            |
| Zahra: gate check, training, erase tool, fixes, decision page (P3, P7, P9, P14, P17) | 24           | Pilot delivery                                  |
| Joseph: baseline, success criteria, client feedback (P1, P8, P16)                    | 6            | Pilot delivery                                  |
| Chleo: volume, client talks, DPAs, decision (P2, P4, P11, P18)                       | 5            | Pilot delivery                                  |
| Joseph: 30-minute review per client report (P12, P15)                                | 1.5          | Per-run cost, 48 EUR each                       |

Pilot delivery: 35 hours x 95 EUR = 3,325 EUR. Together with commercial readiness (3,850 EUR) and development (5,273 EUR), this is the one-time investment of 12,448 EUR used in
`roi_risk_assessment.md`.

## Dependencies

| Dependency                                   | Needed for           | If it is late                                                                                          |
| -------------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------ |
| 2 to 3 clients agree to an AI-assisted pilot | P4, everything after | Pilot moves. Gate 1 is planned for the first days of Sprint 1, so Chleo can ask clients right after it |
| Lawyer available for the DPA review          | P6, then P11         | Real data cannot be loaded (Gate 2). Book the lawyer in week 1                                         |
| External security reviewer available         | P10                  | Same, Gate 2 blocks. Book in Sprint 1                                                                  |
| OpenAI and LangSmith sign DPAs               | P6                   | Both offer standard DPAs online; low risk                                                              |
| Pilot clients deliver their data on time     | P12, P15             | Sprint 3 and 4 slip; the decision moves with them                                                      |
| Joseph has time next to client work          | P1, P12 to P16       | Chleo protects 8 hours per sprint for him                                                              |

## Definition of done (every pilot story)

- The acceptance in the story's "so that" is shown, not just claimed (for example, a measured time, a signed document, a passed review).
- No client data outside that client's isolated environment.
- The owner has shown the result in the sprint review, and Chleo has accepted it.
- Any change to cost, time, or risk is written into `roi_risk_assessment.md` or
  `strategic_plan.md` the same sprint.
