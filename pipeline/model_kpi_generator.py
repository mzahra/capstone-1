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
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# One running log of every pipeline/loader run's real LLM cost, across datasets and over time,
# so "what has this actually cost so far" is answerable from one file instead of hunting
# through each report_*.json separately. JSON Lines, not a single JSON array: a run appends one
# line and never has to read-modify-write the whole file, so a crash mid-run can never corrupt
# an earlier run's already-recorded entry.
COST_LOG_PATH = Path(__file__).resolve().parent.parent / "outputs" / "llm_costs.jsonl"

MODEL = "gpt-4o-mini"

# gpt-4o-mini's real published rate (https://openai.com/api/pricing/), not an estimate.
INPUT_PRICE_PER_1M_USD = 0.15
OUTPUT_PRICE_PER_1M_USD = 0.60
# Approximate, checked 2026-09-03 (EUR/USD near 1.16). Cost at this model's rate is fractions
# of a cent per run either way, so precision here doesn't change any conclusion drawn from it.
USD_TO_EUR = 0.86

# Every real API call this process makes, in order, so a pipeline run can report what it
# actually spent instead of a guess. Cleared by reset_cost_log() at the start of a run.
_call_log: list[dict] = []


def _record_call(label: str, usage) -> None:
    """Logs one chat.completions call's real token usage and cost. `usage` is the `usage`
    object OpenAI returns on every response; skipped defensively if a response ever lacks one."""
    if usage is None:
        return
    prompt_tokens = usage.prompt_tokens
    completion_tokens = usage.completion_tokens
    cost_usd = (
        prompt_tokens / 1_000_000 * INPUT_PRICE_PER_1M_USD
        + completion_tokens / 1_000_000 * OUTPUT_PRICE_PER_1M_USD
    )
    _call_log.append(
        {
            "label": label,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
        }
    )


def reset_cost_log() -> None:
    """Clears the call log. Call this before a pipeline run so cost_summary() reflects only
    that run's calls, not ones left over from an earlier run in the same process."""
    _call_log.clear()


def cost_summary() -> dict:
    """Real cost of every call logged since the last reset_cost_log(), at gpt-4o-mini's actual
    per-token rate. USD is the currency OpenAI actually bills in; cost_eur applies the fixed
    approximate rate above."""
    total_prompt = sum(c["prompt_tokens"] for c in _call_log)
    total_completion = sum(c["completion_tokens"] for c in _call_log)
    total_usd = sum(c["cost_usd"] for c in _call_log)
    return {
        "calls": len(_call_log),
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
        "cost_usd": round(total_usd, 6),
        "cost_eur": round(total_usd * USD_TO_EUR, 6),
        "by_call": list(_call_log),
    }


def append_cost_log(run_label: str, **extra) -> dict | None:
    """Appends this run's cost_summary() as one line to COST_LOG_PATH, tagged with run_label
    (for example "run_pipeline:cfpb" or "load_generic_json:openfoodfacts") and any extra
    context (db path, output path, and so on). Returns the summary, or None and does nothing
    if no call was actually logged (nothing meaningful to record)."""
    summary = cost_summary()
    if summary["calls"] == 0:
        return None
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run": run_label,
        **extra,
        **summary,
    }
    COST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(COST_LOG_PATH, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    return summary

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
   chart stays readable instead of showing every category. Never GROUP BY a raw identifier
   column, that means any column ending in "_id", and also any column whose name contains
   "code", "key", or "ref" (for example "product_code", a barcode, is exactly as unreadable to
   a business user as "product_id" would be). Also treat a column as an identifier, regardless
   of its name, whenever its "distinct" count shown below is close to that table's row count,
   a column where nearly every value is different from every other value behaves like an
   identifier even if its name gives no hint at all. Either way, the values are unreadable
   hashes, codes, or numbers, not something a business user can recognize. Group by a category,
   name, type, status, or date column instead, one with a modest distinct count relative to the
   row count. If the only breakdown available for a table is by a raw identifier, skip it and
   use a different table's category-style column instead. All monetary values in this data are in
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
    _record_call("generate_model_and_kpis", resp.usage)
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
    _record_call("fix_kpi_sql", resp.usage)
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
    _record_call("generate_insights", resp.usage)
    return json.loads(resp.choices[0].message.content)


FLATTEN_SCHEMA_PROMPT = """Here is a field catalog for a client's raw JSON export: each
top-level field's name, how often it appears (as a percent of all records), and its type. No
actual values are included, no field's inner structure either, only its own type.

Propose a relational schema:
- A main table: the scalar fields (str/int/float/bool, not object or list) worth keeping, and a
  primary key field, prefer one that looks like a unique identifier (for example containing
  "id" or "code" in its name). The primary key MUST be one of the exact field names below,
  never invented.
- A child table only for a non-scalar field that is genuinely important business content, the
  kind of thing a business user would actually want to see or group data by (for example a
  product's ingredients, its categories, its nutrition breakdown). Do not propose a child table
  for every non-scalar field that happens to exist, most of them will not be important, only
  the ones that are. Aim for a short, focused set, roughly 3 to 8 child tables, not an
  exhaustive one. "kind" is set by the field's type: "list[object]" -> "objects", any other
  "list[...]" -> "values" (one row per item), "object" -> "keyvalue" (one row per key in the
  object). Do not choose which inner fields to keep for an "objects" table, that is decided
  separately once the actual data is available.
- Skip a field entirely if it looks like internal bookkeeping (timestamps, editor or reviewer
  tracking, debug fields, quality or validation flags, internal processing status) rather than
  genuine content about the record itself. A name ending in "_tags" is not itself a reason to
  skip a field, "categories_tags" is exactly the kind of field worth keeping, judge each one on
  whether it represents real business content, not on its suffix. Also skip a field if the same
  underlying thing already has a better, more structured field covering it (prefer
  "ingredients" over "ingredients_text",
  "categories_tags" over "categories", for example). When genuinely unsure whether a field is
  important business content or bookkeeping, leave it out.

Respond with ONLY valid JSON in this exact shape:
{{
  "main_table": {{"name": "...", "primary_key_field": "...", "fields": ["...", "..."]}},
  "child_tables": [
    {{"name": "...", "source_field": "...", "kind": "objects"}},
    {{"name": "...", "source_field": "...", "kind": "values"}},
    {{"name": "...", "source_field": "...", "kind": "keyvalue"}}
  ]
}}

FIELD CATALOG:
{field_catalog}
"""


def propose_flattening_plan(field_catalog: dict) -> dict:
    catalog_lines = "\n".join(
        f"- {name}: {info['present_pct']}% of records, type {'/'.join(info['types'])}"
        for name, info in field_catalog.items()
    )
    prompt = FLATTEN_SCHEMA_PROMPT.format(field_catalog=catalog_lines)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,  # lowest available, for the most run-to-run consistent schema proposal
        max_tokens=4000,  # the catalog itself can be a couple hundred fields, keep headroom
    )
    _record_call("propose_flattening_plan", resp.usage)
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
