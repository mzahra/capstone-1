# Round 1 to Round 2 Decision

## Decision

Keep the same sector and use case: the Data Copilot for a boutique data and analytics
consultancy (Chleo's company). No industry change.

## What changes for Round 2

**1. Test on messier, less structured data**

Round 1 used the Olist dataset: a real but fairly clean, well documented, relational export.
Round 2 adds semi-structured and, where possible, unstructured data sources on top of it (for
example nested JSON, log style exports, free text notes), and messier data in general. This
tests whether the pipeline's profiling and modeling logic generalizes past one tidy relational
shape, which was already flagged as a risk in Round 1 (see `research/opportunities_risks.md`,
"Generalization risk").

Delivered as three datasets, each testing a different shape: Olist (clean, relational), CFPB
Consumer Complaints (messy, mostly one flat table, free text heavy, tested at its full size,
17.4 million rows), and Open Food Facts (genuinely semi-structured JSON, where even the
top-level fields are not consistent record to record, converted into relational tables by an
AI-proposed schema, `pipeline/load_generic_json.py`, not a hand-written one). See
`pipeline/pipeline_documentation.md`'s "Data structure" and "AI-proposed schema" sections for
what each one proved, including a known reliability limit of the AI-proposed approach.

**2. Add a free text quality check**

Round 1's data quality profiling covers structured columns: nulls, duplicates, outliers, key
candidates. It does not look inside free text fields (reviews, comments, notes) at all.

Round 2 adds a quality check pass over free text fields, including a check for private data
inside that free text. A client's raw export can leak personal information through an
unstructured field (a name or email typed into a comment box, for example) even when every
structured column is properly anonymized. A schema level profiler alone would miss this.

This connects directly to the GDPR risk already noted in Round 1
(`research/opportunities_risks.md`: "Client data includes sensitive personal information").
Round 2's `gdpr_documentation.md` should treat free text PII detection as part of the DPIA, not
as a separate concern.

## AI Manager certification requirement

This capstone is also being used as evidence for an AI Manager certification. On top of the
standard Round 2 deliverables, I will provide the following explicit delivery management artifacts to be included:

- User stories
- Clear definition of done
- Acceptance criteria
- Sprint plan
- Timeline

These describe how the Round 2 work itself was planned and delivered (an AI manager's job, not
just the AI system being built), so they get their own place in the repo rather than being
folded into `strategic_plan.md`, which covers the product's go-to-market timeline instead.
