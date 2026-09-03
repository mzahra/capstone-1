"""
A dataset-agnostic loader for nested JSON Lines sources. Instead of a human hand-coding which
fields matter and which nested arrays become which child tables (which is how Round 1's Olist
and CFPB loaders work), this module asks the AI to propose that structure from the shape of the
data alone, then applies the proposal with plain deterministic code. This is the same pattern
already used for KPIs elsewhere in this pipeline: the AI proposes, and real code executes and
checks the result, the AI's proposal is never trusted blindly. This is the loader actually used
for Open Food Facts in Round 2, see pipeline_documentation.md for the full story, including a
real reliability limitation this loader has and how it is currently mitigated
(propose_flattening_plan_consensus).

Privacy rule, non-negotiable: the AI only ever sees field NAMES, TYPES, and PRESENCE PERCENTAGES
(build_field_catalog), never actual field VALUES. A brand-new source has not been through any
redaction pass yet (that only exists for tables already in SQLite, see text_quality.py), so
sending real sample values to an LLM at this stage could leak personal data before there is any
chance to check for it. Structure alone is enough to decide "this list of objects should be a
child table", it does not require seeing what is actually inside any given record. A child
table's own inner columns are discovered separately, deterministically, from the real data
(discover_object_fields), the AI is never asked to choose those either.

Usage as a library:
    from load_generic_json import load_json_lines_generically
    load_json_lines_generically(records_iterable, db_path)
"""
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

from model_kpi_generator import append_cost_log, cost_summary, propose_flattening_plan, reset_cost_log

MIN_FIELD_PRESENT_PCT = 5.0  # a field present in fewer than this % of all records is dropped
INNER_FIELD_SAMPLE_SIZE = 50  # records peeked at to discover an "objects" table's inner keys
MAX_INNER_FIELDS = 20  # a safety cap on one field's own inner keys


def _type_name(value) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if value is None:
        return "null"
    return type(value).__name__


def _field_type(value) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        if value and isinstance(value[0], dict):
            return "list[object]"
        item_types = {_type_name(v) for v in value} or {"empty"}
        return f"list[{'|'.join(sorted(item_types))}]"
    return _type_name(value)


def build_field_catalog(jsonl_path: Path, min_present_pct: float = MIN_FIELD_PRESENT_PCT) -> dict:
    """Streams the whole file once, field name and type only, never a value, and returns every
    top-level field present in at least min_present_pct of all records. This is deliberately
    built from the true full file, not a small sample: a shallow guess from 50 records cannot
    tell a field that is genuinely rare from one that just missed the sample, real presence
    percentages across the actual data are a much stronger signal for the AI to reason about."""
    field_counts: dict[str, int] = defaultdict(int)
    field_types: dict[str, set] = defaultdict(set)
    total = 0
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            total += 1
            for key, value in record.items():
                field_counts[key] += 1
                field_types[key].add(_field_type(value))

    total = total or 1
    return {
        key: {"present_pct": round(field_counts[key] / total * 100, 1), "types": sorted(types)}
        for key, types in field_types.items()
        if field_counts[key] / total * 100 >= min_present_pct
    }


def discover_object_fields(records: list[dict], source_field: str, max_fields: int = MAX_INNER_FIELDS) -> list[str]:
    """For a "list[object]" field, finds the inner keys actually used across a sample, in
    first-seen order, capped at max_fields. No AI judgment needed here the way there was for
    top-level field selection: an individual nested object (one ingredient, one packaging
    entry) typically has a small, consistent set of keys, not hundreds of competing candidates,
    so just keeping what is actually there is enough."""
    seen: list[str] = []
    seen_set: set[str] = set()
    for record in records:
        items = record.get(source_field)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in item:
                if key not in seen_set:
                    seen_set.add(key)
                    seen.append(key)
                    if len(seen) >= max_fields:
                        return seen
    return seen


def enrich_plan_with_object_fields(plan: dict, sample_records: list[dict]) -> dict:
    """The AI's plan says which fields become "objects" child tables, but is not asked to pick
    their inner columns anymore (see FLATTEN_SCHEMA_PROMPT), that is filled in here instead,
    deterministically, from the real data."""
    for child in plan.get("child_tables", []):
        if child.get("kind", "objects") == "objects" and not child.get("fields"):
            child["fields"] = discover_object_fields(sample_records, child["source_field"])
    return plan


def _clean_field_names(fields, exclude: str | None = None) -> list[str]:
    """The AI's "fields" list is JSON it produced, not a guarantee: an entry can turn out to be
    the wrong type (a nested dict instead of a plain string, confirmed as a real crash, not a
    hypothetical one) or a duplicate. Keeps only non-empty strings, in order, deduplicated, and
    without `exclude` (typically the primary key, added back separately by the caller)."""
    seen = set()
    cleaned = []
    for f in fields or []:
        if not isinstance(f, str) or not f or f == exclude or f in seen:
            continue
        seen.add(f)
        cleaned.append(f)
    return cleaned


def main_table_columns(plan: dict) -> list[str]:
    """The single source of truth for the main table's column order: primary key first, then
    its other fields, deduplicated. The AI's "fields" list is not guaranteed to already include
    or exclude the primary key field, both create_tables_from_plan and the insert logic must
    agree on the same list, or the two disagree on column count."""
    main = plan["main_table"]
    pk_field = main["primary_key_field"]
    return [pk_field, *_clean_field_names(main["fields"], exclude=pk_field)]


def child_table_columns(plan: dict, child: dict) -> list[str]:
    """Same idea for a child table: the foreign key column first (named after the main table's
    primary key), then the child's own columns, which depend on its "kind":
      - "objects" (a list of dicts, e.g. ingredients): the AI's chosen inner fields.
      - "values" (a list of plain values, e.g. category tags): a single "value" column.
      - "keyvalue" (a nested object with a varying key set, e.g. a nutrient breakdown): a
        "key" and a "value" column, one row per key in the object.
    Falls back to "objects" for a plan that predates the "kind" field, for compatibility."""
    pk_field = plan["main_table"]["primary_key_field"]
    kind = child.get("kind", "objects")
    if kind == "values":
        extra_cols = ["value"]
    elif kind == "keyvalue":
        extra_cols = ["key", "value"]
    else:
        # The AI is no longer asked for this directly, see enrich_plan_with_object_fields,
        # which fills it in from the real data before this function is ever called. .get(),
        # not child["fields"], since the AI's own JSON output no longer includes this key at
        # all, only enrichment adds it.
        extra_cols = _clean_field_names(child.get("fields"), exclude=pk_field)
    return [pk_field, *extra_cols]


def drop_all_tables(conn: sqlite3.Connection) -> None:
    """Clears every table in the database, not just ones the current plan happens to name.
    Needed because two different runs against the same db_path can propose different table
    names (this is expected, not a bug, the AI's proposal can reasonably vary), and
    create_tables_from_plan on its own only ever drops tables the current plan reuses, leaving
    an older run's differently-named tables behind. Confirmed as a real problem: testing the
    same file repeatedly left over 30 stale tables from earlier runs still in the database."""
    tables = [
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    ]
    for table in tables:
        conn.execute(f'DROP TABLE IF EXISTS "{table}"')


def create_tables_from_plan(conn: sqlite3.Connection, plan: dict) -> None:
    drop_all_tables(conn)

    main = plan["main_table"]
    pk_field = main["primary_key_field"]
    main_cols = main_table_columns(plan)

    other_cols_sql = "".join(f', "{f}" TEXT' for f in main_cols[1:])
    conn.execute(f'CREATE TABLE "{main["name"]}" ("{pk_field}" TEXT PRIMARY KEY{other_cols_sql})')

    for child in plan.get("child_tables", []):
        child_cols = child_table_columns(plan, child)
        kind = child.get("kind", "objects")
        # A "keyvalue" table's "value" column is usually numeric (a nutrient amount, for
        # example), NUMERIC affinity lets SQLite store it as a real number when it can, unlike
        # TEXT affinity, which would coerce every value to its string form on insert and break
        # AVG()/SUM() in generated KPI SQL later.
        col_types = {
            "key": "TEXT",
            "value": "NUMERIC" if kind == "keyvalue" else "TEXT",
        }
        other_cols_sql = "".join(f', "{f}" {col_types.get(f, "TEXT")}' for f in child_cols[1:])
        conn.execute(f'CREATE TABLE "{child["name"]}" ("{pk_field}" TEXT{other_cols_sql})')


def _coerce_sql_value(value):
    """SQLite cannot bind a list or dict directly. The AI's proposed field list is a plan, not
    a guarantee, a field that looks scalar in the schema sample can still turn out to be a list
    or nested object in some other record, real data is messy record to record. Rather than
    crash on the first such case 25,000 records in, this serializes it to a JSON string."""
    if isinstance(value, (list, dict)):
        return json.dumps(value, default=str)
    return value


def flatten_record_with_plan(record: dict, plan: dict) -> tuple[dict, dict[str, list[dict]]]:
    """One raw record -> one main table row, plus a dict of child table name -> list of rows.
    Every field read defensively with .get(), since the AI's proposed field list is never
    guaranteed to match every record exactly, real data is messy record to record."""
    main = plan["main_table"]
    pk_field = main["primary_key_field"]
    pk_value = record.get(pk_field)

    # Uses the same cleaned column lists create_tables_from_plan used to build the tables, not
    # the raw plan["...']["fields"] again, so a malformed entry (confirmed real: a nested dict
    # where a plain field name was expected) can never disagree between the two.
    main_row = {f: _coerce_sql_value(record.get(f)) for f in main_table_columns(plan)}

    child_rows: dict[str, list[dict]] = {}
    for child in plan.get("child_tables", []):
        kind = child.get("kind", "objects")
        raw = record.get(child["source_field"])
        rows = []

        if kind == "objects":
            object_fields = [f for f in child_table_columns(plan, child) if f != pk_field]
            for item in (raw or []):
                if not isinstance(item, dict):
                    continue  # this record's value for this field isn't shaped as expected, skip it, not crash
                row = {f: _coerce_sql_value(item.get(f)) for f in object_fields}
                row[pk_field] = pk_value
                rows.append(row)

        elif kind == "values":
            for item in (raw or []):
                if isinstance(item, (list, dict)):
                    continue  # not actually a plain value in this record, skip it defensively
                rows.append({pk_field: pk_value, "value": item})

        elif kind == "keyvalue":
            if isinstance(raw, dict):
                for key, value in raw.items():
                    rows.append({pk_field: pk_value, "key": key, "value": _coerce_sql_value(value)})

        child_rows[child["name"]] = rows

    return main_row, child_rows


CONSENSUS_RUNS = 3  # how many times to ask the AI to propose a schema before taking the union


def propose_flattening_plan_consensus(field_catalog: dict, num_runs: int = CONSENSUS_RUNS) -> dict:
    """Calls propose_flattening_plan num_runs times against the same catalog and takes the
    union of child tables found across all runs, deduplicated by source_field, not by table
    name. This is a direct, tested mitigation for a confirmed problem, not a hypothetical one:
    3 identical runs against Open Food Facts, same code, same catalog, temperature 0, produced
    2 matching results and 1 that silently dropped the nutrient breakdown table in favor of a
    much shallower one. Deduplicating by source_field, not name, matters because the AI can
    label the very same field differently run to run (confirmed: "nutritional_info" versus
    "nutriments" for the same "nutriments" field), so comparing table names would undercount
    how much the runs actually agreed."""
    plans = [propose_flattening_plan(field_catalog) for _ in range(num_runs)]

    main_table = plans[0]["main_table"]
    seen_main_fields = set(main_table.get("fields") or [])
    for plan in plans[1:]:
        for f in plan["main_table"].get("fields") or []:
            if isinstance(f, str) and f not in seen_main_fields:
                seen_main_fields.add(f)
                main_table["fields"].append(f)

    seen_source_fields = set()
    child_tables = []
    for plan in plans:
        for child in plan.get("child_tables", []):
            source = child.get("source_field")
            if not source or source in seen_source_fields:
                continue
            seen_source_fields.add(source)
            child_tables.append(child)

    return {"main_table": main_table, "child_tables": child_tables}


def load_json_lines_generically(jsonl_path: Path, db_path: Path, max_records: int | None = None) -> dict:
    """Reads a local JSON Lines file, asks the AI to propose a relational schema from its
    structure, then applies that plan to every record, mechanically. Returns the plan used and
    the row counts loaded, so the caller can see exactly what the AI decided."""
    reset_cost_log()  # this loader run's cost only, not a previous run's if called twice in one process
    print("1/3 Scanning the full file for a field catalog (names and types only, no values)...")
    catalog = build_field_catalog(jsonl_path)
    print(f"   {len(catalog)} fields present in >= {MIN_FIELD_PRESENT_PCT}% of all records")

    print(f"2/3 Asking the AI to propose a relational schema ({CONSENSUS_RUNS} times, taking the union)...")
    plan = propose_flattening_plan_consensus(catalog)
    print(f"   Proposed main table: {plan['main_table']['name']}")
    print(f"   Proposed child tables: {[c['name'] for c in plan.get('child_tables', [])]}")

    # A small sample only, to discover each "objects" table's actual inner keys, see
    # discover_object_fields. The AI itself never sees this, or any other record content.
    inner_sample: list[dict] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if len(inner_sample) >= INNER_FIELD_SAMPLE_SIZE:
                break
            line = line.strip()
            if not line:
                continue
            try:
                inner_sample.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    plan = enrich_plan_with_object_fields(plan, inner_sample)

    print("3/3 Applying the plan to every record...")
    conn = sqlite3.connect(db_path)
    create_tables_from_plan(conn, plan)

    main_name = plan["main_table"]["name"]
    main_cols = main_table_columns(plan)
    main_placeholders = ", ".join("?" for _ in main_cols)

    row_counts = defaultdict(int)
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if max_records and i >= max_records:
                break
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            main_row, child_rows = flatten_record_with_plan(record, plan)
            conn.execute(
                f'INSERT OR IGNORE INTO "{main_name}" VALUES ({main_placeholders})',
                [main_row.get(f) for f in main_cols],
            )
            row_counts[main_name] += 1

            for child in plan.get("child_tables", []):
                rows = child_rows.get(child["name"], [])
                if not rows:
                    continue
                child_cols = child_table_columns(plan, child)
                placeholders = ", ".join("?" for _ in child_cols)
                conn.executemany(
                    f'INSERT INTO "{child["name"]}" VALUES ({placeholders})',
                    [[row.get(f) for f in child_cols] for row in rows],
                )
                row_counts[child["name"]] += len(rows)

    conn.commit()
    conn.close()
    append_cost_log(f"load_generic_json:{db_path.stem}", jsonl_path=str(jsonl_path), db_path=str(db_path))
    return {"plan": plan, "row_counts": dict(row_counts), "cost": cost_summary()}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Loads a raw JSON Lines file into SQLite, letting the AI propose the "
        "relational schema from the data's structure, not a hand-written one."
    )
    parser.add_argument("--jsonl", type=Path, required=True, help="path to the raw JSON Lines file")
    parser.add_argument("--db", type=Path, required=True, help="path to write the SQLite database to")
    parser.add_argument("--max-records", type=int, default=None, help="optional cap on how many records to load")
    parser.add_argument(
        "--plan-out", type=Path, default=None,
        help="path to save the AI's proposed schema plan as JSON. Defaults to "
        "outputs/schema_plan_<db filename>.json",
    )
    args = parser.parse_args()

    # Saved by default, not opt-in: the AI's proposal is a real, reviewable decision, the same
    # way a KPI's SQL or a recommended data model always gets written to outputs/, not just
    # printed to the terminal and lost.
    plan_out = args.plan_out or (
        Path(__file__).resolve().parent.parent / "outputs" / f"schema_plan_{args.db.stem}.json"
    )

    args.db.parent.mkdir(parents=True, exist_ok=True)
    result = load_json_lines_generically(args.jsonl, args.db, max_records=args.max_records)

    print("\nPlan the AI proposed:")
    print(f"  main table: {result['plan']['main_table']['name']}")
    print(f"  child tables: {[c['name'] for c in result['plan'].get('child_tables', [])]}")
    print("\nRow counts:")
    for table, count in result["row_counts"].items():
        print(f"  {table}: {count:,}")
    print(f"\nDatabase written to {args.db}")

    cost = result["cost"]
    print(
        f"LLM cost for the schema proposal: {cost['calls']} calls, {cost['total_tokens']:,} tokens, "
        f"${cost['cost_usd']:.6f} (~€{cost['cost_eur']:.6f}), logged to outputs/llm_costs.jsonl"
    )

    plan_out.parent.mkdir(parents=True, exist_ok=True)
    plan_out.write_text(
        json.dumps({"plan": result["plan"], "row_counts": result["row_counts"], "cost": cost}, indent=2)
    )
    print(f"Schema plan saved to {plan_out}")
