"""
The AI step: takes the profiling report from profiling.py and asks an LLM to

  1. recommend a dimensional data model (fact + dimension tables, with rationale)
  2. propose business KPIs with the SQL to compute each one
  3. flag the top data-quality issues in plain language
  4. suggest 2-3 forward-looking data-science opportunities the schema could support

...then, after the proposed KPI SQL is actually executed against the database,
a second call turns the real KPI values into a plain-language insight report.

Both calls go through an OpenAI client wrapped by LangSmith's `wrap_openai`,
so every prompt/response is traced automatically as long as LANGSMITH_TRACING
and LANGSMITH_API_KEY are set in .env. This is the "AI can be observed and
discussed transparently" piece of Round 1.
"""
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = "gpt-4o-mini"

tracing_on = os.environ.get("LANGSMITH_TRACING", "").lower() == "true" and bool(
    os.environ.get("LANGSMITH_API_KEY")
)

try:
    from langsmith.wrappers import wrap_openai

    client = wrap_openai(OpenAI(api_key=os.environ["OPENAI_API_KEY"]))
    if tracing_on:
        print(f"LangSmith tracing is ON (project: {os.environ.get('LANGSMITH_PROJECT', 'default')})")
    else:
        print(
            "LangSmith tracing is OFF: set LANGSMITH_TRACING=true and LANGSMITH_API_KEY "
            "in .env to record traces."
        )
except Exception as e:
    # LangSmith not configured -- pipeline still runs, just untraced. Printed loudly
    # because a silent fallback here is exactly the kind of thing that looks fine
    # until you check LangSmith and find nothing was ever recorded.
    print(f"LangSmith tracing could not be set up ({e}); continuing without it.")
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def summarize_profile(profile: dict, max_tables: int | None = None) -> str:
    """Compress the raw profiling dict into a compact text block for the prompt."""
    lines = []
    tables = list(profile["tables"].items())
    if max_tables:
        tables = tables[:max_tables]

    for table, info in tables:
        size_note = f"{info['row_count']} rows, {info['duplicate_rows']} duplicate rows"
        if info.get("sampled"):
            size_note += (
                f" (column stats below are from a {info['sample_size']:,}-row sample of this "
                f"table, not an exact scan of all {info['row_count']:,} rows, since it is too "
                f"large to load whole)"
            )
        lines.append(f"\nTABLE {table} ({size_note})")
        if info["pk_candidates"]:
            lines.append(f"  PK candidates: {', '.join(info['pk_candidates'])}")
        for col, stats in info["columns"].items():
            line = (
                f"  - {col}: {stats['dtype']}, null={stats['null_pct']}%, "
                f"distinct={stats['distinct_count']}, outliers={stats['outlier_count']}, "
                f"e.g. {stats['sample_values']}"
            )
            # Sample values above are already redacted (see text_quality.py), so it is safe
            # to also tell the model what kind of PII was detected, as counts only.
            if stats.get("free_text_pii"):
                pii = stats["free_text_pii"]
                pii_summary = ", ".join(
                    f"{entity} in {e['pct']}% of {pii['sample_size']} sampled values"
                    for entity, e in pii["entities"].items()
                )
                line += f" | POSSIBLE PII DETECTED: {pii_summary}"
            if stats.get("casing_issues"):
                line += f" | INCONSISTENT CASING/FORMAT: {len(stats['casing_issues'])} value(s) affected"
            lines.append(line)

    lines.append("\nFOREIGN KEY CANDIDATES (confirmed by value overlap):")
    for fk in profile["fk_candidates"]:
        lines.append(
            f"  - {fk['child_table']}.{fk['child_column']} -> "
            f"{fk['parent_table']}.{fk['parent_column']} ({fk['value_overlap_pct']}% overlap)"
        )
    return "\n".join(lines)


MODEL_KPI_PROMPT = """You are a senior data consultant onboarding a new client's raw database export.
Below is a schema/quality profile of their tables. Based ONLY on this profile:

1. Recommend a dimensional model: one fact table and its dimension tables, with a short rationale.
2. Propose 5-7 business KPIs a CEO/ops lead would care about. For each, give valid SQLite SQL
   that computes it against the tables/columns shown (use exact table/column names from the
   profile). SQLite divides two integers as integer division, so any rate, average, or
   percentage MUST cast at least one side to REAL (for example CAST(x AS REAL) / y) to avoid
   silently returning 0. At least 2 of the KPIs MUST be a breakdown by category (a GROUP BY
   query returning several rows, for example revenue by product category, orders by payment
   type, or reviews by score) so the results can be shown as a chart, not just a single number.
   Every breakdown query MUST include ORDER BY the value column DESC and LIMIT 10, so the
   chart stays readable instead of showing every category. Never GROUP BY a raw id column
   (any column ending in "_id"), since the values are unreadable hashes or numbers, not
   something a business user can recognize. Group by a category, name, type, status, or date
   column instead. If the only breakdown available for a table is by raw id, skip it and use
   a different table's category-style column instead. All monetary values in this data are in
   Brazilian Real (BRL), not USD or EUR. Never use a "$" sign anywhere in names or reasoning.
   If a lookup/translation table exists that maps a code column to a readable English name
   (for example a "_translation" table), join it and use the English name column instead of
   the raw code, so results are readable to an English-speaking reader.
3. List the top 3-5 data quality issues found (plain language, reference the specific table/column).
   If any column is marked "POSSIBLE PII DETECTED" or "INCONSISTENT CASING/FORMAT" in the
   profile below, always include it as one of these issues, since it affects whether this data
   is safe to show a client as-is.
4. Suggest 2-3 forward-looking data-science opportunities this schema could support (e.g. churn
   prediction, demand forecasting) -- one sentence each, do not build them, just suggest.

Respond with ONLY valid JSON in this exact shape:
{{
  "recommended_model": {{"fact_table": "...", "dimensions": ["..."], "rationale": "..."}},
  "kpis": [{{"name": "...", "sql": "...", "why_it_matters": "..."}}],
  "quality_findings": ["..."],
  "data_science_opportunities": ["..."]
}}

SCHEMA PROFILE:
{profile_summary}
"""

INSIGHT_PROMPT = """You are writing a short business-facing report for a non-technical client (a CEO).
Here are the KPI results computed from their database:

{kpi_results}

And these are the data quality issues found in their raw data:

{quality_findings}

All monetary values are in Brazilian Real (BRL). Refer to money as "BRL" or "R$", never "$"
(a bare "$" would wrongly imply US dollars).

Write 4-6 plain-language insight bullets. Each bullet should say what the numbers show and why it
matters for the business (not statistics jargon). Where a quality issue affects trust in a number,
say so honestly.

Respond with ONLY valid JSON: {{"insights": ["...", "..."]}}
"""


def generate_model_and_kpis(profile: dict) -> dict:
    prompt = MODEL_KPI_PROMPT.format(profile_summary=summarize_profile(profile))
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return json.loads(resp.choices[0].message.content)


FIX_SQL_PROMPT = """This SQLite query failed:

{sql}

Error: {error}

Here are the exact column names that exist in this database. A column name with a space or
punctuation (for example "Timely response?") must be wrapped in double quotes to be used in
SQL; a name like Timely_response does not exist just because it looks like a cleaned-up version
of one:

{schema_hint}

Fix the query so it runs successfully, using only these exact column names, and keep the same
intent as the original query. Respond with ONLY the corrected SQL, no explanation, no markdown
code fences.
"""


def schema_hint_from_profile(profile: dict) -> str:
    """A compact table -> exact column names list. Deliberately not the full stats profile
    used in the original recommendation prompt, since fixing a failed query only needs to know
    what the real column names are, not their null rates or sample values."""
    lines = []
    for table, info in profile["tables"].items():
        columns = ", ".join(f'"{c}"' for c in info["columns"])
        lines.append(f"{table}: {columns}")
    return "\n".join(lines)


def fix_kpi_sql(sql: str, error: str, schema_hint: str) -> str:
    prompt = FIX_SQL_PROMPT.format(sql=sql, error=error, schema_hint=schema_hint)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    fixed = resp.choices[0].message.content.strip()
    # Defensive: the prompt asks for no markdown fences, but an LLM cannot be trusted to
    # always follow that, so any ```sql ... ``` wrapper is stripped if it shows up anyway.
    if fixed.startswith("```"):
        fixed = fixed.strip("`")
        if fixed.lower().startswith("sql"):
            fixed = fixed[3:]
        fixed = fixed.strip()
    return fixed


def generate_insights(kpi_results: dict, quality_findings: list[str]) -> dict:
    prompt = INSIGHT_PROMPT.format(
        kpi_results=json.dumps(kpi_results, indent=2, default=str),
        quality_findings="\n".join(f"- {q}" for q in quality_findings),
    )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    return json.loads(resp.choices[0].message.content)


if __name__ == "__main__":
    from pathlib import Path

    profile_path = Path(__file__).resolve().parent.parent / "outputs" / "profiling.json"
    if not profile_path.exists():
        raise FileNotFoundError(
            f"{profile_path} not found. Run `python pipeline/profiling.py` first."
        )

    profile = json.loads(profile_path.read_text())

    print("Calling the AI for a data model and KPI recommendation...")
    result = generate_model_and_kpis(profile)

    output_path = profile_path.parent / "model_kpis.json"
    output_path.write_text(json.dumps(result, indent=2))
    print(f"Saved to {output_path}\n")

    print("Recommended model:")
    print(f"  fact table: {result['recommended_model']['fact_table']}")
    print(f"  dimensions: {result['recommended_model']['dimensions']}")
    print(f"  why: {result['recommended_model']['rationale']}\n")

    print(f"KPIs proposed ({len(result['kpis'])}):")
    for kpi in result["kpis"]:
        print(f"  - {kpi['name']}")

    print(f"\nQuality findings ({len(result['quality_findings'])}):")
    for finding in result["quality_findings"]:
        print(f"  - {finding}")

    print(f"\nData science opportunities ({len(result['data_science_opportunities'])}):")
    for opp in result["data_science_opportunities"]:
        print(f"  - {opp}")
