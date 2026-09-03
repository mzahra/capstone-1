"""
Loads the full CFPB Consumer Complaint Database into its own local SQLite database
(data/warehouse_cfpb.db). This is the Round 2 "second client": messier, mostly one flat table,
and free-text heavy, unlike Olist's clean, relational data, and at a genuinely large scale
(about 17.4 million rows, about 30 GB as CSV). This tests whether the pipeline generalizes past
one tidy schema shape (see research/opportunities_risks.md), including at a scale well past
Olist's roughly 1.5 million rows.

The full CFPB export is a public, no-key-needed bulk download. This script downloads it once
(cached locally, not committed to git), then streams the CSV out of the zip in chunks straight
into SQLite. It never holds more than one chunk in memory, which is what makes it safe to run
on the full export instead of a smaller slice.

Loading the whole table this way is fine, since SQLite is disk-based, not memory-based. The
part that would break on this much data is profiling.py's per-column stats, which used to pull
a whole table into pandas. See profiling.py's SAMPLE_ROW_THRESHOLD for how that is handled now.

Usage:
    python pipeline/load_cfpb_data.py
"""
import sqlite3
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "cfpb"
ZIP_PATH = DATA_DIR / "complaints.csv.zip"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "warehouse_cfpb.db"

BULK_DOWNLOAD_URL = "https://files.consumerfinance.gov/ccdb/complaints.csv.zip"
TABLE_NAME = "complaints"
CHUNK_SIZE = 100_000  # rows read and inserted at a time, keeps memory bounded regardless of file size


def download_bulk_zip() -> None:
    if ZIP_PATH.exists():
        print(f"Using already-downloaded {ZIP_PATH.name} ({ZIP_PATH.stat().st_size / 1e6:.0f} MB)")
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading CFPB bulk export from {BULK_DOWNLOAD_URL} (about 1.4 GB, one time only)...")
    urlretrieve(BULK_DOWNLOAD_URL, ZIP_PATH)
    print(f"Downloaded to {ZIP_PATH}")


def load_all_rows_into_sqlite() -> int:
    """Streams the CSV out of the zip in chunks and appends each chunk straight into SQLite.
    Never holds more than one chunk in memory at a time."""
    conn = sqlite3.connect(DB_PATH)
    total = 0
    with zipfile.ZipFile(ZIP_PATH) as zf:
        csv_name = next(n for n in zf.namelist() if n.endswith(".csv"))
        with zf.open(csv_name) as raw:
            for i, chunk in enumerate(pd.read_csv(raw, chunksize=CHUNK_SIZE)):
                chunk.to_sql(TABLE_NAME, conn, if_exists="replace" if i == 0 else "append", index=False)
                total += len(chunk)
                print(f"  ...{total:,} rows loaded")
    conn.close()
    return total


if __name__ == "__main__":
    download_bulk_zip()
    print(
        "Loading the full CFPB export into SQLite, streamed in chunks. This is about 17.4 "
        "million rows, so it takes a while, expect somewhere around 15 to 30 minutes."
    )
    total = load_all_rows_into_sqlite()
    print(f"\nLoaded {total:,} rows into '{TABLE_NAME}' table -> {DB_PATH}")
