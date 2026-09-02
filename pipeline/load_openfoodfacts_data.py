"""
Loads a slice of Open Food Facts into its own local SQLite database
(data/warehouse_openfoodfacts.db). This is the Round 2 "third client": genuinely
semi-structured JSON, not just a structured table with a free-text column (that was CFPB).

Each product record in the source is a deeply nested JSON object, and the schema is not even
consistent record to record (two products can have almost no top-level keys in common). This
script does the conversion step that pipeline_documentation.md has flagged as out of scope since
Round 1 ("deeply nested JSON... needs a separate conversion step first"): it flattens each
record into one row in a `products` table, plus one row per item in three nested arrays/dicts,
in three child tables:

  - `ingredients`: from each product's `ingredients` array (one row per ingredient)
  - `categories`: from each product's `categories_tags` array (one row per category tag)
  - `nutriments`: from each product's `nutriments` dict (one row per nutrient key/value)

All three child tables share `product_code`, a real foreign key back to `products.code`, which
gives profiling.py's foreign key detection genuine relationships to confirm. CFPB never
exercised that code path, since it loaded as a single flat table.

The source file is 12.8 GB compressed with several million records. This does not download or
decompress the whole thing: it streams directly from the URL and stops once MAX_PRODUCTS
well-formed records have been collected, closing the connection early. Each accepted record's
original raw JSON line is written to RAW_PATH as it streams by, so the raw input, not just the
tables derived from it, ends up on disk too.

Usage:
    python pipeline/load_openfoodfacts_data.py
"""
import gzip
import sqlite3
from pathlib import Path

import requests

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "warehouse_openfoodfacts.db"
# The raw, unflattened JSON records are also kept on disk, one per line, exactly as they came
# from the source, before flatten_product() ever touches them. Olist's raw CSVs and CFPB's raw
# zip both already sit in data/, this is the same thing for Open Food Facts: the actual raw
# input, not just the processed SQLite tables derived from it.
RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "openfoodfacts" / "raw_products.jsonl"

SOURCE_URL = "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"
# Open Food Facts blocks the default python-requests user agent (returns an HTML 403 page,
# which is itself gzip-compressed, so it looks like valid input until json.loads fails on it).
# A descriptive User-Agent is required, not just polite practice, see their API usage docs.
HEADERS = {"User-Agent": "DataCopilotCapstone-Student/1.0"}

MAX_PRODUCTS = 25_000  # a bounded slice, not the full multi-million-record export, see README


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS ingredients;
        DROP TABLE IF EXISTS categories;
        DROP TABLE IF EXISTS nutriments;

        CREATE TABLE products (
            code TEXT PRIMARY KEY,
            product_name TEXT,
            brands TEXT,
            quantity TEXT,
            nova_group TEXT,
            product_type TEXT
        );
        CREATE TABLE ingredients (
            product_code TEXT,
            ingredient_id TEXT,
            ingredient_text TEXT,
            percent_estimate REAL,
            vegan TEXT,
            vegetarian TEXT
        );
        CREATE TABLE categories (
            product_code TEXT,
            category_tag TEXT
        );
        CREATE TABLE nutriments (
            product_code TEXT,
            nutrient_name TEXT,
            value REAL
        );
        """
    )


def flatten_product(product: dict) -> tuple[tuple, list[tuple], list[tuple], list[tuple]]:
    """One nested JSON record -> one products row, plus child rows for its nested
    ingredients/categories/nutriments. Every field read defensively with .get(), since real
    records do not all share the same keys."""
    code = product.get("code")

    products_row = (
        code,
        product.get("product_name"),
        product.get("brands"),
        product.get("quantity"),
        str(product.get("nova_group")) if product.get("nova_group") is not None else None,
        product.get("product_type"),
    )

    ingredient_rows = [
        (
            code,
            ing.get("id"),
            ing.get("text"),
            ing.get("percent_estimate"),
            ing.get("vegan"),
            ing.get("vegetarian"),
        )
        for ing in (product.get("ingredients") or [])
        if isinstance(ing, dict)
    ]

    category_rows = [
        (code, tag)
        for tag in (product.get("categories_tags") or [])
        if isinstance(tag, str)
    ]

    nutriment_rows = [
        (code, key, value)
        for key, value in (product.get("nutriments") or {}).items()
        if isinstance(value, (int, float))
    ]

    return products_row, ingredient_rows, category_rows, nutriment_rows


def stream_and_load() -> int:
    import json

    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)

    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)

    resp = requests.get(SOURCE_URL, stream=True, headers=HEADERS)
    resp.raise_for_status()
    gz = gzip.GzipFile(fileobj=resp.raw)

    kept = 0
    try:
        with open(RAW_PATH, "wb") as raw_out:
            for line in gz:
                if not line.strip():
                    continue
                try:
                    product = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if not product.get("code") or not product.get("product_name"):
                    continue  # not well-formed enough to be useful, skip

                raw_out.write(line if line.endswith(b"\n") else line + b"\n")

                products_row, ingredient_rows, category_rows, nutriment_rows = flatten_product(product)
                conn.execute(
                    "INSERT OR IGNORE INTO products VALUES (?, ?, ?, ?, ?, ?)", products_row
                )
                conn.executemany(
                    "INSERT INTO ingredients VALUES (?, ?, ?, ?, ?, ?)", ingredient_rows
                )
                conn.executemany("INSERT INTO categories VALUES (?, ?)", category_rows)
                conn.executemany("INSERT INTO nutriments VALUES (?, ?, ?)", nutriment_rows)

                kept += 1
                if kept % 5_000 == 0:
                    conn.commit()
                    print(f"  ...{kept:,} products loaded")

                if kept >= MAX_PRODUCTS:
                    break
    finally:
        conn.commit()
        conn.close()
        resp.close()  # stops the stream early, the rest of the 12.8 GB is never downloaded

    return kept


if __name__ == "__main__":
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Streaming Open Food Facts, stopping at {MAX_PRODUCTS:,} well-formed products...")
    total = stream_and_load()
    print(f"\nLoaded {total:,} products (plus their ingredients/categories/nutriments) -> {DB_PATH}")
    print(f"Raw records saved -> {RAW_PATH}")
