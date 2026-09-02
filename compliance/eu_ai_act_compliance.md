# EU AI Act Compliance

This is a coursework capstone, written to show the reasoning a real AI Manager would document.
It is not legal advice. A real deployment would need review by counsel before going to a
client.

## Risk classification, step by step

**Step 1: Is this an AI system under the Act?** Yes. It uses a machine learning model (an LLM,
OpenAI gpt-4o-mini) to infer outputs (a data model recommendation, KPI definitions, a written
insight report) from input data, which then influence a human decision (what a consultant sends
to a client).

**Step 2: Is it a prohibited practice under Article 5?** No. It does not do social scoring,
manipulation, biometric categorization, emotion inference in the workplace, or any of the other
practices listed as prohibited. It is a business intelligence tool.

**Step 3: Is it high-risk under Annex III?** No. Annex III's high-risk categories are things
like biometric identification, critical infrastructure, education access, employment decisions
(recruitment, task allocation, monitoring, promotion or termination), access to essential
private or public services (credit scoring, insurance pricing, benefits eligibility), law
enforcement, migration and asylum, and the administration of justice. This system profiles a
client's own business data (their e-commerce orders, or in the CFPB test case, complaints filed
against companies) and drafts an internal report for that client's own use. It does not decide
whether any individual gets a job, a loan, insurance, a benefit, or access to a service. It is a
B2B analytics tool used inside one company, not a decision made about an individual. None of
Annex III applies.

**Step 4: Is the consultancy a provider of a general-purpose AI model?** No. The GPAI provider
obligations in Article 53 fall on OpenAI, which trains and releases the underlying model. The
consultancy is a deployer, calling that model through an API to build a specific application.
Deployer obligations are much lighter than provider obligations, and mostly consist of using
the model within its intended purpose and following the provider's instructions, both of which
this project does.

**Step 5: Do the Article 50 transparency obligations apply?**

- *Article 50(1), disclosing an AI interaction to a natural person*: does not apply. Nobody
  chats with this system. It is a batch pipeline that produces a document.
- *Article 50(2), marking AI-generated content as artificially generated*: this is the closest
  one, since the insight text and the recommended-model rationale are AI-written. But Article
  50(2) has a carve-out: it does not apply where the content has undergone a process of human
  review and a natural or legal person holds editorial responsibility for its publication. This
  project's mandatory human consultant review before a report reaches a client (see
  `strategic_plan.md`'s pilot phase gate) is exactly that carve-out. The consultancy, not the
  AI, takes editorial responsibility for what it sends a client.
- *Article 50(4), labeling AI-generated text on matters of public interest*: does not apply.
  This is a private report delivered to one paying client, not published content on a matter of
  public interest.

**Conclusion: minimal risk.** No Annex III category applies, and the mandatory human review step
already built into this project's design keeps it out of Article 50(2)'s marking obligation too.

## Mandatory requirements summary

None of the Act's mandatory requirements apply at minimal risk. This section exists anyway,
since it is worth being explicit about what would change the answer, and what is done
voluntarily despite nothing requiring it:

- If the pipeline were ever used to help decide something about an individual (for example,
  scoring which of a client's customers to prioritize for debt collection, or influencing a
  hiring decision), that specific use would need to be re-assessed against Annex III, most
  likely as high-risk, triggering a full conformity assessment, technical documentation under
  Annex IV, and human oversight requirements. This project's scope is deliberately kept to
  aggregate business reporting, not decisions about individuals, exactly to avoid that.
- Voluntarily adopted anyway, because Chleo asked for exactly this and it is good practice
  regardless of what the Act requires: every AI decision is logged and reviewable (LangSmith),
  a human reviews every report before it reaches a client, and the AI is told to flag data
  quality problems honestly rather than smoothing them over (see
  `research/opportunities_risks.md`).

## Conformity assessment summary

A formal conformity assessment (Article 43) is a high-risk system requirement and is not
legally required here. A short internal self-assessment was still done, in that spirit:

- **Intended purpose:** drafting a first-pass data quality, modeling, and business insight
  report for a data consultancy's internal use, always reviewed by a consultant before reaching
  a client.
- **Data used:** aggregate schema statistics and computed KPI numbers only reach the model, per
  Section 4 of `pipeline/pipeline_documentation.md`. Free text is scanned for personal data
  locally, before anything is redacted and shown to the model, see `text_quality.py`.
- **Known failure modes checked:** wrong or invalid SQL (mitigated with a retry loop that feeds
  the real error back to the model, up to 5 attempts, and shows what still fails rather than
  hiding it), a recommended model that does not fit flat, single-table data (shown, not hidden,
  see the CFPB test in `pipeline/pipeline_documentation.md`), and PII missed by the local scan on
  non-English text (documented, not silently assumed away).
- **Outcome:** no blocking issues found for the intended purpose above. The main condition on
  this holding true is that the human review step stays mandatory, see the risk matrix in
  `roi_risk_assessment.md`, "over reliance" risk.

## Technical documentation outline

Not legally required at minimal risk (Annex IV applies to high-risk systems), but provided as a
skeleton, modeled on Annex IV's structure, in case this project is ever assessed at a higher
risk tier later (for example, if the consultancy extended it toward a use case that does touch
Annex III).

1. General description of the system
   1.1. Intended purpose and the consultancy's use case
   1.2. How the system interacts with other systems (OpenAI API, LangSmith, SQLite)
   1.3. Versions and update history
2. Detailed description of the elements and development process
   2.1. Methods and steps for development (see `pipeline/pipeline_documentation.md`)
   2.2. Design specifications, including the model/KPI/insight prompts
   2.3. Data requirements: datasheets for the training-adjacent data used (here: the schema
        profile and KPI results the model sees, not training data, since this uses a
        pre-trained model via API, not a custom-trained one)
   2.4. Human oversight measures: the mandatory consultant review gate
3. Monitoring, functioning, and control
   3.1. Capabilities and limitations, see `pipeline/pipeline_documentation.md`'s limits section
   3.2. Foreseeable misuse
   3.3. Performance metrics used, see `roi_risk_assessment.md`
4. Risk management system, see `roi_risk_assessment.md`'s risk matrix
5. Changes made through the system's lifecycle (change log)
