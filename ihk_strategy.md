# AI Strategy: Data Copilot

This file follows the AI strategy structure of the IHK AI Manager presentation: who we are, our AI
ambition, the AI strategy house, the use case ideas and how we prioritized them, the decision,
the AI Use Case Canvas, and the implementation checklist. Details live in the other project
files, linked in each section.

## 1. About us

Chleo runs a small data and analytics consultancy, about 10 to 30 people. Clients are small and
mid-sized companies from many sectors. They hire the firm to make sense of their data: reports,
dashboards, and "tell us what our numbers mean."

Every new client starts the same way. A raw data export arrives, and a senior consultant spends
an estimated 4 to 8 hours checking it, understanding it, choosing KPIs, and writing a first
report, before any real analysis starts.

**Our mission:** "We help growing companies understand their data quickly and turn it into
decisions, with personal attention and full transparency about how we got there."

Our edge against large consulting firms is speed and personal attention. Our risk is that every
new client costs the same amount of senior time, so we cannot grow without hiring.

## 2. Our goals

1. **Faster first results:** a client sees a first read on their data in days, not weeks.
2. **More capacity without hiring:** senior consultants spend their time on analysis and advice,
   not on routine preparation.
3. **Same quality for every client:** every client gets the same careful data check, no matter
   which consultant does the work.
4. **Trust:** we can explain every result to the client, including every step the AI took.

## 3. Our AI ambition

> **AI does the first draft. Our consultants make the judgment. Every AI step can be explained
> to the client.**

We want to be the fastest and most trusted way for a growing company to understand its data. AI
takes over the routine first pass, so our people can spend their time where clients value it
most. We never hand a client an AI result that a consultant has not checked.

## 4. AI strategy house

| Part of the house | What it means for us |
|---|---|
| **Roof: AI ambition** | AI does the first draft, consultants make the judgment, every step is explainable (section 3) |
| **Pillar 1: AI use cases** | Collect ideas, score them on strategic value and ease of implementation, start with the best one (sections 5 to 7) |
| **Pillar 2: Prerequisites** | Data: clients already send us their data. Skills: an AI Manager in the team, consultants as domain experts. Budget: a one-time investment of about 12,400 EUR. Time: an 8-week pilot. Legal: GDPR processor agreements and an EU AI Act check (minimal risk) |
| **Pillar 3: Implementation** | Inform and train consultants, run a pilot with 2 to 3 real clients next to the manual process, then decide with real numbers (section 9) |
| **Foundation: our non-negotiables** | A consultant reviews every AI result before a client sees it. Personal data is removed before anything leaves our machine. Client data is never mixed between clients |

## 5. Use case ideas

We collected four ideas where AI could support our business.

| # | Idea | What it would do |
|---|---|---|
| A | **Data Copilot for client onboarding** | Takes a new client's raw data export and produces, in minutes, a data quality check, a proposed data model, calculated KPIs, and a plain-language first report, for a consultant to review |
| B | **AI proposal writer** | Turns notes from a sales call into a first draft of a project proposal and offer |
| C | **Internal knowledge search** | One search across all past projects, so consultants can reuse earlier analyses, SQL, and dashboards |
| D | **"Ask your data" chatbot for clients** | Clients ask questions about their own dashboards in plain language and get answers without a consultant |

## 6. Prioritization matrix

Each idea is scored from 1 (low) to 5 (high) on two criteria:

- **Strategic value:** how much it supports our goals and our edge (speed, capacity, quality,
  trust).
- **Ease of implementation:** do we have the data, the know-how, and the budget, and how much
  has to change.

| # | Idea | Strategic value | Ease of implementation | Reasoning |
|---|---|---|---|---|
| A | Data Copilot | **5** | **4** | Hits all four goals. Happens with every new client. Clients send us the data anyway. A working prototype already exists and was tested on three very different datasets |
| B | Proposal writer | 2 | 4 | Easy to build, but saves only some sales time. General AI tools already do this well, so it gives us no edge |
| C | Knowledge search | 3 | 2 | Useful, but past project files are spread across many places. Hard part: client A's data must never appear in a search for client B. Needs strict access rules first |
| D | Client chatbot | 4 | 2 | A possible new product, but the AI would answer clients directly without a consultant check. That breaks our foundation rule, and a wrong answer goes straight to the client |

```
Strategic value
  5 |                          A
  4 |      D
  3 |      C
  2 |                          B
  1 |
    +----+----+----+----+----+
         1    2    3    4    5
              Ease of implementation
```

**Result:** Data Copilot (A) is the only idea that is both high value and easy to implement.

## 7. Our decision

**We start with Data Copilot for client onboarding.**

Why:

- It solves our biggest bottleneck: senior time spent on every new client.
- It fits our ambition exactly: AI drafts, the consultant checks, every step is logged.
- It is the lowest-risk start: a working prototype exists, and the pilot can be stopped after
  two weeks if the numbers do not support it.

Ideas C and D stay on the list for later. D in particular becomes possible once Data Copilot has
shown, with real clients, that the AI's work can be trusted.

## 8. AI Use Case Canvas: Data Copilot

### Description

A new client's raw data export goes in. Within minutes, Data Copilot produces a first draft
onboarding report: how clean the data is, how the tables connect, a proposed data model, the
KPIs that matter with their real values, and plain-language findings. Personal data is detected
and removed before anything leaves our machine. A consultant reviews the draft (about 30
minutes) before the client sees it.

### Values

**1. How does it support our AI ambition?**
It is our ambition in practice: AI does the routine first pass, the consultant makes the
judgment, and every AI decision is logged so we can explain it to the client.

**2. What future competitive advantage does it give us?**
- Speed: a first read for the client in days, not weeks. Large firms are slower, and self-service
  BI tools assume the client already has a data team and a data warehouse.
- Consistency: every client gets the same careful check.
- Transparency: we can show a client exactly what the AI did. Most AI tools cannot.
- A path to new business: the report suggests follow-on data science projects to the client.

**3. What is the economic impact?**
- An estimated 4 to 8 hours of senior consultant time replaced by a 30-minute review, per new
  client.
- One-time investment: about 12,400 EUR. Then 220 EUR per month and 48 EUR per client.
- Base case (6 hours saved, 2 new clients per month): pays back after about 15 months, 72%
  return over 3 years.
- If manual work is already fast or clients are fewer, it may not pay off. The pilot measures
  both in its first two weeks, before most of the money is spent. See `roi_risk_assessment.md`.

**Value types:** quality improvement, resource efficiency, efficiency gain, customer
satisfaction. All four apply.

### Ease of implementation score

Each statement is scored from 1 (does not apply) to 5 (fully applies).

| Area | Statement | Score | Why |
|---|---|---|---|
| **Data / technology** | We have access to the required data | 5 | Every onboarding starts with the client sending us their data export, so access is always there |
| | We have the required amount of data | 5 | One client export is enough. Tested from small data up to 17.4 million rows |
| | We have the required data quality | 3 | We do not control the quality of client data. The tool handles messy data and reports quality problems, but poor data limits how useful the KPIs are. Not yet tested on real client data |
| | **Total** | **13** | |
| **Algorithm** | We know the technical resources that lead to a solution | 5 | The prototype is built and working |
| | A similar problem has been solved with AI elsewhere | 4 | Parts exist inside large tools (for example Power BI Copilot), but not as one tool for consultancies |
| | We know techniques that work for this problem | 3 | Works well on tables. Proposing a structure for nested data is not yet fully reliable, so a human check stays |
| | **Total** | **12** | |
| **Processes / systems** | Few processes must change | 4 | Onboarding stays the same. The consultant reviews a draft instead of building it |
| | Few systems must be adapted | 4 | Runs on its own. Needs one isolated, secure environment per client |
| | Few organizational changes are needed | 4 | One short training and a fixed review step |
| | **Total** | **12** | |
| **Expertise** | Required technology know-how is available | 3 | Available through the AI Manager, but in one person only. A risk if that person is away |
| | Required domain knowledge is available | 5 | Our consultants are the domain experts |
| | Required training can happen in reasonable time | 5 | About 4 hours of training for consultants |
| | **Total** | **13** | |
| **Time to verified proof of concept** | Under 3 months = 5 points, 4 to 6 months = 4, 7 to 9 months = 3, 10 to 12 months = 2, over 12 months = 1 | **5** | Prototype done. The pilot with real clients takes 8 weeks |

**Overall ease of implementation: 55 of 65 points.**

## 9. Implementation checklist

### Organizational aspects

**How is the implementation organized?** Four two-week sprints, 8 weeks in total, with three
decision gates. Details, owners, and capacity in `delivery_plan.md`.

| Sprint | What happens | Gate |
|---|---|---|
| 1. Discovery | Measure the real manual time and client volume. Agree with 2 to 3 pilot clients | Gate 1: does it pay off? |
| 2. Pilot build | Secure environment per client, security review, data deletion tool, signed agreements | Gate 2: is it safe? |
| 3. Pilot run | First two real clients, next to the manual process | |
| 4. Pilot run and decision | Third client, client feedback, comparison | Gate 3: go or no-go |

**Who are the key stakeholders and decision makers?**

| Stakeholder | Role |
|---|---|
| Chleo, owner | Sponsor. Makes the go/no-go decision at each gate |
| Zahra, AI Manager | Plans and builds the solution, owns delivery |
| Joseph, senior consultant | Pilot lead. Runs and reviews the client reports, measures the time |
| Consultants | Daily users. Review every AI draft before a client sees it |
| Pilot clients | Provide real data, agree to AI-assisted onboarding, give feedback |
| People in the client's data | Not involved directly, but their personal data must be protected (GDPR) |

### Financial aspects

**What does it cost?**

| | Cost |
|---|---|
| Development (done) | 5,273 EUR |
| Making it ready for real clients: security review, secure environments, legal agreements | 3,850 EUR |
| Running the pilot: team time | 3,325 EUR |
| **One-time investment** | **12,448 EUR** |
| Hosting and support | 220 EUR per month |
| Consultant review | 48 EUR per client |
| AI usage | about 0.001 EUR per client, measured |

**How is it financed?** From the consultancy's own budget. The gates limit the risk: only about
570 EUR of new spend (the Discovery measurements) comes before the first go/no-go check.

### Risks

**What are the biggest risks?**

| Risk | How we handle it |
|---|---|
| Manual work is already faster than we think, or there are fewer new clients | Measured in the first sprint. Clear stop rule (Gate 1) |
| Personal data in the client's data reaches the AI provider | Detected and removed on our machine first. A consultant checks every report |
| The AI proposes a wrong KPI or wrong numbers | Every KPI is calculated on the real data, not just suggested. Failed calculations are retried and shown, not hidden. The consultant reviews everything |
| Consultants rely on the AI too much | The review step is permanent, not a pilot measure. Training explains what to check |
| Depending on one AI provider | Cost is tiny today. A second provider is planned as part of full rollout |
| Know-how sits with one person | Setup and run instructions are written. Consultants are trained to run it themselves |

Full risk matrix: `roi_risk_assessment.md`.

### Exit criteria: when do we stop?

We stop or rescope the project if:

- **Gate 1:** the measured manual time and client volume are below the break-even table, so the
  tool would not pay back within 3 years.
- **Gate 2:** the security review finds a serious problem we cannot fix in the sprint, or a
  pilot client does not sign the data processing agreement.
- **Gate 3:** AI-assisted onboarding does not get under 1 hour of consultant time, any pilot
  report contains unremoved personal data, consultants or clients do not find the report useful,
  or the ROI with real numbers is negative over 3 years.
- **At any time:** pilot clients do not agree to AI-assisted onboarding, or a change at the AI
  provider (price, terms, data handling) makes the business case or the legal basis fail.

### Timeline

| When | What |
|---|---|
| Done | Working prototype, tested on three very different kinds of client data |
| Weeks 1 to 2 | Discovery and Gate 1 |
| Weeks 3 to 4 | Pilot build and Gate 2 |
| Weeks 5 to 8 | Pilot with 2 to 3 real clients, then Gate 3 |
| After a "go" | Standard part of every new client onboarding within 2 months |
