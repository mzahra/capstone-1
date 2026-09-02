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

from profiling import DB_PATH, profile_database
from model_kpi_generator import fix_kpi_sql, generate_insights, generate_model_and_kpis, schema_hint_from_profile

DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "outputs" / "report.json"


MAX_ROWS_PER_KPI = 50  # a KPI is meant to be a summary, not a full table dump
MAX_KPI_ATTEMPTS = 5  # the first try plus up to 4 retries, each feeding the SQL error back to the model


def execute_kpi_sql(conn: sqlite3.Connection, kpis: list[dict], schema_hint: str) -> list[dict]:
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

                # The prompt tells the AI not to group a breakdown by a raw id column, but an
                # LLM cannot be trusted to always follow an instruction, so this is enforced
                # here too: a breakdown whose label column is a raw id is not useful to a
                # business reader (it is a hash or a number, not a name), so it is dropped
                # rather than shown as a chart with unreadable labels.
                if len(entry["rows"]) > 1 and cols[0].endswith("_id"):
                    entry["status"] = "skipped"
                    entry["error"] = f"grouped by raw id column '{cols[0]}', not useful to show as a chart"
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

    print("1/4 Profiling database...")
    profile = profile_database(db_path)

    print("2/4 Asking the AI to recommend a data model + KPIs...")
    model_kpis = generate_model_and_kpis(profile)

    print("3/4 Executing generated KPI SQL against the database...")
    schema_hint = schema_hint_from_profile(profile)
    conn = sqlite3.connect(db_path)
    kpi_results = execute_kpi_sql(conn, model_kpis.get("kpis", []), schema_hint)
    translate_category_values(conn, kpi_results)
    conn.close()

    ok_count = sum(1 for k in kpi_results if k["status"] == "ok")
    print(f"   {ok_count}/{len(kpi_results)} KPIs computed successfully")

    quality_findings = model_kpis.get("quality_findings", [])

    print("4/4 Generating plain-language business insights...")
    insights = generate_insights(kpi_results, quality_findings)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
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
    print("Run the dashboard with: streamlit run dashboard/app.py")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=None, help="path to the SQLite database to run the pipeline against")
    parser.add_argument("--out", type=Path, default=None, help="path to write report.json to")
    args = parser.parse_args()

    main(db_path=args.db, output_path=args.out)
