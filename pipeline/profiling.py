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

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "warehouse.db"

FK_OVERLAP_THRESHOLD = 0.9  # 90%+ of child values found in parent -> treat as real FK


def get_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return [r[0] for r in rows]


def profile_table(conn: sqlite3.Connection, table: str) -> dict:
    df = pd.read_sql(f'SELECT * FROM "{table}"', conn)
    n_rows = len(df)
    duplicate_rows = int(df.duplicated().sum())

    columns = {}
    pk_candidates = []
    for col in df.columns:
        s = df[col]
        null_count = int(s.isna().sum())
        distinct_count = int(s.nunique(dropna=True))
        is_unique_nonnull = null_count == 0 and distinct_count == n_rows and n_rows > 0

        outlier_count = 0
        if pd.api.types.is_numeric_dtype(s) and s.dropna().shape[0] > 4:
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                outlier_count = int(((s < lower) | (s > upper)).sum())

        columns[col] = {
            "dtype": str(s.dtype),
            "null_count": null_count,
            "null_pct": round(null_count / n_rows * 100, 2) if n_rows else 0,
            "distinct_count": distinct_count,
            "outlier_count": outlier_count,
            "sample_values": [str(v) for v in s.dropna().unique()[:3].tolist()],
        }
        if is_unique_nonnull:
            pk_candidates.append(col)

    return {
        "table": table,
        "row_count": n_rows,
        "duplicate_rows": duplicate_rows,
        "pk_candidates": pk_candidates,
        "columns": columns,
    }


def detect_fk_candidates(conn: sqlite3.Connection, profiles: dict[str, dict]) -> list[dict]:
    """Cross-table FK candidates confirmed by value overlap, not just name match."""
    fks = []
    for table, profile in profiles.items():
        for col in profile["columns"]:
            if not (col.endswith("_id") or col.endswith("id")):
                continue
            for other_table, other_profile in profiles.items():
                if other_table == table:
                    continue
                if col not in other_profile["pk_candidates"]:
                    continue
                child_vals = pd.read_sql(f'SELECT DISTINCT "{col}" FROM "{table}"', conn)[col].dropna()
                if child_vals.empty:
                    continue
                parent_vals = set(
                    pd.read_sql(f'SELECT DISTINCT "{col}" FROM "{other_table}"', conn)[col].dropna()
                )
                overlap = child_vals.isin(parent_vals).mean()
                if overlap >= FK_OVERLAP_THRESHOLD:
                    fks.append(
                        {
                            "child_table": table,
                            "child_column": col,
                            "parent_table": other_table,
                            "parent_column": col,
                            "value_overlap_pct": round(overlap * 100, 1),
                        }
                    )
    return fks


def profile_database() -> dict:
    conn = sqlite3.connect(DB_PATH)
    tables = get_tables(conn)
    profiles = {t: profile_table(conn, t) for t in tables}
    fk_candidates = detect_fk_candidates(conn, profiles)
    conn.close()
    return {"tables": profiles, "fk_candidates": fk_candidates}


if __name__ == "__main__":
    import json
    from pathlib import Path

    result = profile_database()

    output_path = Path(__file__).resolve().parent.parent / "outputs" / "profiling.json"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, default=str))

    print(f"Profile written to {output_path}")
    print(json.dumps(result, indent=2, default=str)[:1000])
