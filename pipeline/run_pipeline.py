"""
End-to-end POC: raw client export -> quality/schema profile -> AI-recommended
data model + KPIs -> executed KPI values -> AI-written business insights.

Usage:
    python pipeline/load_data.py       # once, to build data/warehouse.db
    python pipeline/run_pipeline.py    # runs the full pipeline, writes outputs/report.json

The dashboard (dashboard/app.py) reads outputs/report.json.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from profiling import (
    DB_PATH,
    IDENTIFIER_CARDINALITY_THRESHOLD,
    column_cardinality_ratio,
    column_is_known_key,
    looks_like_identifier,
    profile_database,
)
from model_kpi_generator import (
    append_cost_log,
    cost_summary,
    fix_kpi_sql,
    generate_insights,
    generate_model_and_kpis,
    reset_cost_log,
    schema_hint_from_profile,
)

DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "outputs" / "report.json"


MAX_ROWS_PER_KPI = 50  # a KPI is meant to be a summary, not a full table dump
MAX_KPI_ATTEMPTS = 5  # the first try plus up to 4 retries, each feeding the SQL error back to the model


def execute_kpi_sql(conn: sqlite3.Connection, kpis: list[dict], schema_hint: str, profile: dict) -> list[dict]:
    """
    The AI is asked for structured JSON, but an LLM response is never 100% guaranteed to
    match the exact schema every time, so every field is read defensively with .get()
    instead of kpi["..."], which would crash the whole pipeline over one missing field.

    A KPI whose SQL fails is retried up to MAX_KPI_ATTEMPTS times: the exact SQLite error is
    fed back to the model, along with the real column names, and it is asked to fix the query.
    This matters most for column names with spaces or punctuation (for example
    "Timely response?"), which the AI sometimes rewrites into a clean-looking name that does
    not actually exist, like Timely_response.
    """
    results = []
    for kpi in kpis:
        entry = {
            "name": kpi.get("name", "Unnamed KPI"),
            "sql": kpi.get("sql", ""),
            "why_it_matters": kpi.get("why_it_matters", ""),
        }
        if not entry["sql"]:
            entry["rows"] = []
            entry["status"] = "failed"
            entry["error"] = "AI response had no SQL for this KPI"
            entry["attempts"] = 0
            results.append(entry)
            continue

        sql = entry["sql"]
        attempt_errors = []
        for attempt in range(1, MAX_KPI_ATTEMPTS + 1):
            try:
                cur = conn.execute(sql)
                cols = [d[0] for d in cur.description]
                raw_rows = cur.fetchmany(MAX_ROWS_PER_KPI)
                entry["sql"] = sql
                entry["rows"] = [dict(zip(cols, row)) for row in raw_rows]
                entry["status"] = "ok"
                entry["attempts"] = attempt
                if attempt_errors:
                    entry["attempt_errors"] = attempt_errors

                # The prompt tells the AI not to group a breakdown by a raw identifier column,
                # but an LLM cannot be trusted to always follow an instruction, so this is
                # enforced here too: a breakdown whose label column is a raw identifier is not
                # useful to a business reader (it is a hash, code, or number, not a name), so it
                # is dropped rather than shown as a chart with unreadable labels.
                #
                # Three independent checks, since no single one catches everything:
                #  - looks_like_identifier: name-based, catches "_id"/"code"/"key"/"ref". Misses a
                #    naming convention it has not seen yet.
                #  - column_is_known_key: confirmed by FK/PK detection elsewhere in the profile.
                #    Catches a foreign key even when it legitimately repeats many times in a
                #    child table, so its own cardinality there looks low. This is what actually
                #    catches Open Food Facts' "ingredients.product_code": only about 11%
                #    distinct within that table (many ingredients per product), so the
                #    cardinality check alone would have missed it, but it is a confirmed foreign
                #    key to products.code.
                #  - column_cardinality_ratio: a column whose values are almost all distinct
                #    behaves like an identifier regardless of name, catches a genuine primary
                #    key that FK/PK detection missed for some other reason.
                cardinality_ratio = column_cardinality_ratio(cols[0], profile)
                is_high_cardinality = (
                    cardinality_ratio is not None and cardinality_ratio >= IDENTIFIER_CARDINALITY_THRESHOLD
                )
                is_known_key = column_is_known_key(cols[0], profile)
                if len(entry["rows"]) > 1 and (looks_like_identifier(cols[0]) or is_known_key or is_high_cardinality):
                    entry["status"] = "skipped"
                    if looks_like_identifier(cols[0]):
                        reason = "name looks like an identifier"
                    elif is_known_key:
                        reason = "confirmed as a key elsewhere in the schema"
                    else:
                        reason = f"{cardinality_ratio:.0%} of its values are distinct"
                    entry["error"] = f"grouped by raw identifier column '{cols[0]}' ({reason}), not useful to show as a chart"
                    entry["rows"] = []
                break
            except Exception as e:
                attempt_errors.append(str(e))
                if attempt == MAX_KPI_ATTEMPTS:
                    entry["sql"] = sql
                    entry["rows"] = []
                    entry["status"] = "failed"
                    entry["error"] = str(e)
                    entry["attempts"] = attempt
                    entry["attempt_errors"] = attempt_errors
                else:
                    sql = fix_kpi_sql(sql, str(e), schema_hint)
        results.append(entry)
    return results


def translate_category_values(conn: sqlite3.Connection, kpi_results: list[dict]) -> None:
    """
    The prompt asks the AI to join any "_translation" lookup table it finds and use the
    English name instead of a raw code, but an LLM cannot be trusted to always do that.
    This is a deterministic backstop: build a code -> English name map straight from the
    database, then replace any matching value in the KPI results in place, regardless of
    what column name or SQL the AI actually used.
    """
    try:
        rows = conn.execute(
            "SELECT product_category_name, product_category_name_english "
            "FROM product_category_name_translation"
        ).fetchall()
    except sqlite3.OperationalError:
        return  # no translation table in this client's data, nothing to do

    translation = {code: english for code, english in rows if code and english}
    if not translation:
        return

    for kpi in kpi_results:
        for row in kpi.get("rows", []):
            for key, value in list(row.items()):
                if isinstance(value, str) and value in translation:
                    row[key] = translation[value]


def main(db_path=None, output_path=None):
    db_path = db_path or DB_PATH
    output_path = output_path or DEFAULT_OUTPUT_PATH
    reset_cost_log()  # this run's cost only, not a previous run's if main() is called twice in one process

    print("1/4 Profiling database...")
    profile = profile_database(db_path)

    print("2/4 Asking the AI to recommend a data model + KPIs...")
    model_kpis = generate_model_and_kpis(profile)

    print("3/4 Executing generated KPI SQL against the database...")
    schema_hint = schema_hint_from_profile(profile)
    conn = sqlite3.connect(db_path)
    kpi_results = execute_kpi_sql(conn, model_kpis.get("kpis", []), schema_hint, profile)
    translate_category_values(conn, kpi_results)
    conn.close()

    ok_count = sum(1 for k in kpi_results if k["status"] == "ok")
    print(f"   {ok_count}/{len(kpi_results)} KPIs computed successfully")

    quality_findings = model_kpis.get("quality_findings", [])

    print("4/4 Generating plain-language business insights...")
    insights = generate_insights(kpi_results, quality_findings)

    cost = cost_summary()
    append_cost_log(f"run_pipeline:{Path(db_path).stem}", db_path=str(db_path), output_path=str(output_path))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cost": cost,
        "profile_summary": {
            "tables": {
                t: {
                    "row_count": p["row_count"],
                    "duplicate_rows": p["duplicate_rows"],
                    "sampled": p.get("sampled", False),
                    "sample_size": p.get("sample_size"),
                }
                for t, p in profile["tables"].items()
            },
            "fk_candidates": profile["fk_candidates"],
        },
        "recommended_model": model_kpis.get(
            "recommended_model", {"fact_table": "unknown", "dimensions": [], "rationale": "not provided"}
        ),
        "quality_findings": quality_findings,
        "data_science_opportunities": model_kpis.get("data_science_opportunities", []),
        "kpis": kpi_results,
        "insights": insights["insights"],
    }

    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nDone. Report written to {output_path}")
    print(
        f"LLM cost this run: {cost['calls']} calls, {cost['total_tokens']:,} tokens, "
        f"${cost['cost_usd']:.6f} (~€{cost['cost_eur']:.6f}), logged to outputs/llm_costs.jsonl"
    )
    print("Run the dashboard with: streamlit run dashboard/app.py")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=None, help="path to the SQLite database to run the pipeline against")
    parser.add_argument("--out", type=Path, default=None, help="path to write report.json to")
    args = parser.parse_args()

    main(db_path=args.db, output_path=args.out)
