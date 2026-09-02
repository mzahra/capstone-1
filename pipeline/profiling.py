"""
Data quality + schema profiling.

For every table in the SQLite DB, computes:
  - column stats (dtype, null %, distinct %, sample values)
  - primary-key candidates (unique + non-null columns)
  - duplicate row counts
  - simple numeric outlier flags (IQR method)
  - foreign-key candidates across tables, confirmed by value overlap
    (not just name matching: a column named the same in two tables only
    counts as a real relationship if most of its values actually appear
    in the candidate parent table)

Output is a plain dict, JSON serialisable, that becomes the input to the
LLM step in model_kpi_generator.py.
"""
import sqlite3
from pathlib import Path

import pandas as pd

from text_quality import (
    check_casing_consistency,
    is_free_text_column,
    redact_sample,
    scan_column_for_pii,
)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "warehouse.db"

FK_OVERLAP_THRESHOLD = 0.9  # 90%+ of child values found in parent -> treat as real FK

# Tables at or below this size are pulled whole into pandas, same as Round 1. Above it, a
# table is sampled instead: loading a client's full table straight into a pandas DataFrame
# does not hold up past a few hundred thousand rows (see pipeline_documentation.md's "Data
# volume" limit), which matters directly for CFPB's roughly 17.4 million row complaints table.
# Row counts always come from a full SQL COUNT(*), never the sample, so those stay exact.
SAMPLE_ROW_THRESHOLD = 100_000


def get_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return [r[0] for r in rows]


def profile_table(conn: sqlite3.Connection, table: str) -> dict:
    n_rows = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    sampled = n_rows > SAMPLE_ROW_THRESHOLD

    if sampled:
        # An evenly spaced sample across the table's row order, not just the first N rows,
        # which would bias toward whatever the source file happened to be sorted by (CFPB's
        # export is roughly chronological, so "first N rows" would mean "oldest complaints
        # only"). SQLite's implicit rowid makes this a single cheap table scan, no ORDER BY
        # RANDOM() sort of the whole table.
        stride = max(n_rows // SAMPLE_ROW_THRESHOLD, 1)
        df = pd.read_sql(f'SELECT * FROM "{table}" WHERE (rowid - 1) % {stride} = 0', conn)
    else:
        df = pd.read_sql(f'SELECT * FROM "{table}"', conn)

    sample_size = len(df)
    duplicate_rows = int(df.duplicated().sum())

    columns = {}
    pk_candidates = []
    for col in df.columns:
        s = df[col]
        null_count = int(s.isna().sum())
        distinct_count = int(s.nunique(dropna=True))
        # Uniqueness can only be checked against what was actually loaded. For a sampled
        # table this means "unique within the sample", not a guarantee across all n_rows.
        is_unique_nonnull = null_count == 0 and distinct_count == sample_size and sample_size > 0

        outlier_count = 0
        if pd.api.types.is_numeric_dtype(s) and s.dropna().shape[0] > 4:
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                outlier_count = int(((s < lower) | (s > upper)).sum())

        sample_values = [str(v) for v in s.dropna().unique()[:3].tolist()]

        # Numeric outlier detection above only covers number columns. These two checks cover
        # what it misses in text columns: private data hidden in free text, and inconsistent
        # casing/formatting in categorical text. See text_quality.py for why both run locally.
        free_text_pii = {}
        casing_issues = {}
        if pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s):
            if is_free_text_column(s):
                free_text_pii = scan_column_for_pii(s)
                sample_values = [redact_sample(v) for v in sample_values]
            else:
                casing_issues = check_casing_consistency(s)

        columns[col] = {
            "dtype": str(s.dtype),
            "null_count": null_count,
            "null_pct": round(null_count / sample_size * 100, 2) if sample_size else 0,
            "distinct_count": distinct_count,
            "outlier_count": outlier_count,
            "sample_values": sample_values,
            "free_text_pii": free_text_pii,
            "casing_issues": casing_issues,
        }
        if is_unique_nonnull:
            pk_candidates.append(col)

    return {
        "table": table,
        "row_count": n_rows,
        "sampled": sampled,
        "sample_size": sample_size if sampled else None,
        "duplicate_rows": duplicate_rows,
        "pk_candidates": pk_candidates,
        "columns": columns,
    }


FK_NAME_HINTS = ("id", "code", "key", "ref")


def _looks_like_identifier(col: str) -> bool:
    lowered = col.lower()
    return any(hint in lowered for hint in FK_NAME_HINTS)


def detect_fk_candidates(conn: sqlite3.Connection, profiles: dict[str, dict]) -> list[dict]:
    """
    Cross-table FK candidates confirmed by value overlap, not just name match. The column name
    only has to loosely look like an identifier (contains "id", "code", "key", or "ref"
    anywhere, not just as a suffix), and does not have to exactly match the parent table's
    primary key column name.

    The exact-name-match version missed real relationships that use a different naming
    convention on each side. Confirmed with Open Food Facts: its child tables use
    "product_code" against the parent table's "code" column, a real relationship, 100% value
    overlap, that the exact-match version found nothing for, since neither the "_id" suffix
    check nor the same-name requirement matched. The broadened check still only ever reports a
    relationship based on real value overlap, a loose name hint is just a cheap way to avoid
    checking every column against every other table's keys.
    """
    fks = []
    for table, profile in profiles.items():
        for col, col_stats in profile["columns"].items():
            if not _looks_like_identifier(col):
                continue
            if col_stats.get("free_text_pii"):
                continue  # a free text column is never a sensible identifier candidate

            child_vals = pd.read_sql(f'SELECT DISTINCT "{col}" FROM "{table}"', conn)[col].dropna()
            if child_vals.empty:
                continue

            for other_table, other_profile in profiles.items():
                if other_table == table:
                    continue
                for parent_col in other_profile["pk_candidates"]:
                    parent_vals = set(
                        pd.read_sql(f'SELECT DISTINCT "{parent_col}" FROM "{other_table}"', conn)[parent_col].dropna()
                    )
                    overlap = child_vals.isin(parent_vals).mean()
                    if overlap >= FK_OVERLAP_THRESHOLD:
                        fks.append(
                            {
                                "child_table": table,
                                "child_column": col,
                                "parent_table": other_table,
                                "parent_column": parent_col,
                                "value_overlap_pct": round(overlap * 100, 1),
                            }
                        )
    return fks


def profile_database(db_path: Path | None = None) -> dict:
    """db_path lets a second "client" database (for example the CFPB warehouse) be profiled
    with the same code, without changing the Olist default used by the dashboard."""
    conn = sqlite3.connect(db_path or DB_PATH)
    tables = get_tables(conn)
    profiles = {t: profile_table(conn, t) for t in tables}
    fk_candidates = detect_fk_candidates(conn, profiles)
    conn.close()
    return {"tables": profiles, "fk_candidates": fk_candidates}


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DB_PATH, help="path to the SQLite database to profile")
    parser.add_argument("--out", type=Path, default=None, help="path to write profiling.json to")
    args = parser.parse_args()

    output_path = args.out or (Path(__file__).resolve().parent.parent / "outputs" / "profiling.json")

    result = profile_database(args.db)

    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, default=str))

    print(f"Profile written to {output_path}")
    print(json.dumps(result, indent=2, default=str)[:1000])
