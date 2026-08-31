"""
Loads every CSV in data/ into a local SQLite database (data/warehouse.db).
This simulates "receiving a raw client export", the starting point for the pipeline.

Usage:
    python pipeline/load_data.py

Expects the Olist Brazilian E-Commerce CSVs (download from Kaggle and drop
into data/), for example olist_orders_dataset.csv, olist_customers_dataset.csv, and so on.
Table names are derived from filenames (olist_ prefix / _dataset suffix stripped).
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "warehouse.db"


def table_name_from_path(csv_path: Path) -> str:
    name = csv_path.stem
    name = re.sub(r"^olist_", "", name)
    name = re.sub(r"_dataset$", "", name)
    return name


def load_all_csvs() -> list[str]:
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"No CSVs found in {DATA_DIR}. Download the Olist dataset from "
            "Kaggle (Brazilian E-Commerce Public Dataset by Olist) and place "
            "the CSVs there."
        )

    conn = sqlite3.connect(DB_PATH)
    loaded = []
    for csv_path in csv_files:
        table = table_name_from_path(csv_path)
        df = pd.read_csv(csv_path)
        df.to_sql(table, conn, if_exists="replace", index=False)
        loaded.append(table)
        print(f"loaded {csv_path.name} -> table '{table}' ({len(df)} rows, {len(df.columns)} cols)")
    conn.close()
    return loaded


if __name__ == "__main__":
    tables = load_all_csvs()
    print(f"\nDatabase ready at {DB_PATH} with {len(tables)} tables: {tables}")
