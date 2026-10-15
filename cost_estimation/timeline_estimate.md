# Timeline Estimate

## Proposed real world rollout

Four two-week sprints. The stories, owners, and capacity behind each sprint are in
`delivery_plan.md`.

| Sprint | Weeks | What happens |
|---|---|---|
| 1: Discovery | 1 to 2 | Measure today's manual onboarding time and client volume, and stop if below break-even (Gate 1). Agree with 2 to 3 pilot clients what "good" looks like. Then start the isolated environment, the DPA template, and consultant training |
| 2: Pilot build | 3 to 4 | Search-and-erase tool, independent security review, signed DPAs with every pilot client (Gate 2) |
| 3: Pilot run | 5 to 6 | Pilot clients 1 and 2, next to the existing manual process. Fix issues before client 3 |
| 4: Pilot run and decision | 7 to 8 | Pilot client 3, client feedback, AI-assisted vs. manual comparison, go or no-go (Gate 3) |
| Full rollout | ongoing | Make it part of the standard onboarding workflow for new clients |

**Total time to a go or no-go decision: 8 weeks.** One extra sprint (10 weeks at most) if a
dependency is late: a pilot client, the lawyer, or the security reviewer.

## Key assumptions

- Pilot clients agree to have their onboarding partly AI assisted, with human review
- No client data needs special compliance handling beyond what is covered in
  `compliance/gdpr_documentation.md`
- Zahra (AI Manager) has 20 hours per week, and Joseph (senior consultant, pilot lead) has about
  8 hours per sprint next to client work, see `delivery_plan.md`
