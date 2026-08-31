"""
Round 1 dashboard. Reads outputs/report.json (produced by pipeline/run_pipeline.py)
and outputs/profiling.json (produced by pipeline/profiling.py), and presents them as
a client facing onboarding report.

Business content (KPIs, charts, insights) comes first. Technical content (the data
model diagram, the full quality check breakdown) is collapsed at the end, since a
client mostly wants the business content, and a consultant reviewing the draft wants
the technical detail available but out of the way.

Usage:
    streamlit run dashboard/app.py
"""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

REPORT_PATH = Path(__file__).resolve().parent.parent / "outputs" / "report.json"
PROFILE_PATH = Path(__file__).resolve().parent.parent / "outputs" / "profiling.json"

st.set_page_config(page_title="Data Copilot: Client Onboarding Report", layout="wide")

# --- Color palette, one accent color per section ---------------------------
COLORS = {
    "title": "#1B4F72",
    "kpi": "#2C6E9E",
    "insights": "#1F8A70",
    "quality": "#B5651D",
    "opportunities": "#6B4FA0",
    "technical": "#555555",
}

# A different color per chart, cycled in order, so charts do not all look the same.
# Kept distinct from the section heading colors above, so a chart is never mistaken
# for belonging to a different section.
CHART_PALETTE = ["#2C6E9E", "#3FA7A0", "#D9736C", "#6B4FA0", "#4C956C", "#117864"]


def style_chart(fig):
    """
    Always white background with black text, no matter the viewer's system or browser
    dark mode setting. Paired with theme=None on st.plotly_chart, since Streamlit would
    otherwise restyle the chart to match the viewer's theme automatically, which is what
    made the earlier "make it black text" fix disappear under dark mode.
    """
    fig.update_layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#000000", size=14),
        xaxis=dict(title_font=dict(size=14, color="#000000"), tickfont=dict(size=12, color="#000000")),
        yaxis=dict(title_font=dict(size=14, color="#000000"), tickfont=dict(size=12, color="#000000")),
        legend=dict(font=dict(color="#000000")),
        margin=dict(t=30),
    )
    return fig

st.markdown(
    f"""
    <style>
    [data-testid="stMetricValue"] {{ color: {COLORS['kpi']}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def section_header(text: str, color: str, level: str = "h2") -> None:
    st.markdown(f"<{level} style='color:{color}'>{text}</{level}>", unsafe_allow_html=True)


if not REPORT_PATH.exists():
    st.error("No report found. Run `python pipeline/run_pipeline.py` first.")
    st.stop()

report = json.loads(REPORT_PATH.read_text())
profile = json.loads(PROFILE_PATH.read_text()) if PROFILE_PATH.exists() else None

st.markdown(f"<h1 style='color:{COLORS['title']}'>Data Copilot: Client Onboarding Report</h1>", unsafe_allow_html=True)
st.caption(f"Generated {report['generated_at']}")


def build_mermaid_erd(profile: dict) -> str:
    """
    Turns the confirmed foreign keys into a Mermaid ER diagram, relationships only
    (no per-column attribute boxes). The full column and key detail is already shown
    right next to this diagram in the "Checks performed" table, so nothing is lost by
    keeping the diagram simple, and a relationships-only diagram is much less likely
    to hit a Mermaid parsing edge case than one listing every column of every table.
    A table with no confirmed relationship to any other table (for example a lookup
    table nothing else joins to) will not appear as a box here.
    """
    lines = ["erDiagram"]
    seen = set()
    for fk in profile["fk_candidates"]:
        pair = tuple(sorted([fk["parent_table"], fk["child_table"]]))
        key = (pair, fk["child_column"])
        if key in seen:
            continue
        seen.add(key)
        lines.append(
            f'    {fk["parent_table"]} ||--o{{ {fk["child_table"]} : "{fk["child_column"]}"'
        )
    return "\n".join(lines)


# --- KPIs, with charts where a KPI has more than one row -------------------
section_header("KPIs", COLORS["kpi"])
st.caption("Monetary figures are in Brazilian Real (BRL), the currency of the source dataset (Olist is a Brazilian e-commerce company). Data covers September 2016 to October 2018 (about 2 years), so totals are cumulative over that period, not annual. Average order value is the item price only, it does not include shipping.")
ok_kpis = [k for k in report["kpis"] if k["status"] == "ok" and k["rows"]]
failed_kpis = [k for k in report["kpis"] if k["status"] != "ok"]

single_value_kpis = [k for k in ok_kpis if len(k["rows"]) == 1 and len(k["rows"][0]) == 1]
chart_kpis = [k for k in ok_kpis if k not in single_value_kpis]


def round_value(v):
    """Floats are rounded to 2 decimal places for display; everything else is untouched."""
    return round(v, 2) if isinstance(v, float) else v


if single_value_kpis:
    cols = st.columns(min(len(single_value_kpis), 4) or 1)
    for i, kpi in enumerate(single_value_kpis):
        value = round_value(next(iter(kpi["rows"][0].values())))
        with cols[i % len(cols)]:
            st.metric(kpi["name"], value)
            st.caption(kpi["why_it_matters"])

for i, kpi in enumerate(chart_kpis):
    st.subheader(kpi["name"])
    df = pd.DataFrame(kpi["rows"])
    label_col, value_col = df.columns[0], df.columns[-1]
    df[value_col] = df[value_col].apply(round_value)
    chart_color = CHART_PALETTE[i % len(CHART_PALETTE)]
    fig = px.bar(df, x=label_col, y=value_col, color_discrete_sequence=[chart_color])
    fig = style_chart(fig)
    st.plotly_chart(fig, use_container_width=True, theme=None)
    st.caption(kpi["why_it_matters"])

# --- Business insights -------------------------------------------------
section_header("Business Insights", COLORS["insights"])
for insight in report["insights"]:
    st.write(f"- {insight}")

# --- Data science opportunities -----------------------------------------
section_header("What Else This Data Could Support", COLORS["opportunities"])
for opp in report["data_science_opportunities"]:
    st.write(f"- {opp}")

# --- Technical details, collapsed ---------------------------------------
with st.expander("Technical details (data model, quality checks)"):
    section_header("Data Quality Findings", COLORS["quality"], level="h3")
    st.markdown("\n".join(f"- {f}" for f in report["quality_findings"]))

    section_header("Checks performed, table by table", COLORS["technical"], level="h3")
    if profile:
        rows = []
        for table, info in profile["tables"].items():
            cols = info["columns"]
            null_cols = {c: s["null_pct"] for c, s in cols.items() if s["null_pct"] > 0}
            worst_null_col = max(null_cols, key=null_cols.get) if null_cols else None
            outlier_total = sum(s["outlier_count"] for s in cols.values())
            rows.append({
                "Table": table,
                "Rows": info["row_count"],
                "Columns checked": len(cols),
                "Duplicate rows": info["duplicate_rows"],
                "Columns with missing values": len(null_cols),
                "Worst missing value column": f"{worst_null_col} ({null_cols[worst_null_col]}%)" if worst_null_col else "none",
                "Outlier values found": outlier_total,
                "Primary key found": ", ".join(info["pk_candidates"]) if info["pk_candidates"] else "none",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.caption("Relationships confirmed between tables (checked by real matching values, not just column names):")
        for fk in profile["fk_candidates"]:
            st.write(
                f"- {fk['child_table']}.{fk['child_column']} -> "
                f"{fk['parent_table']}.{fk['parent_column']} "
                f"({fk['value_overlap_pct']}% of values matched)"
            )
    else:
        st.info("Run `python pipeline/profiling.py` to see the full check by check breakdown here.")
        for table, stats in report["profile_summary"]["tables"].items():
            st.write(f"**{table}**: {stats['row_count']} rows, {stats['duplicate_rows']} duplicate rows")

    section_header("Recommended Data Model", COLORS["technical"], level="h3")
    model = report["recommended_model"]
    st.write(f"**Fact table:** {model['fact_table']}")
    st.write(f"**Dimensions:** {', '.join(model['dimensions'])}")
    st.info(model["rationale"])

    if profile:
        st.caption("Entity-relationship diagram, generated from the actual confirmed keys:")
        mermaid_code = build_mermaid_erd(profile)
        components.html(
            f"""
            <pre class="mermaid">{mermaid_code}</pre>
            <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
            <script>mermaid.initialize({{startOnLoad: true}});</script>
            """,
            height=550,
            scrolling=True,
        )
        st.caption(
            f"More than one table can look like a hub here, since this diagram shows every "
            f"confirmed relationship, not just the fact table. That is normal when data has "
            f"more than one level of detail (for example an order header and its order items). "
            f"The AI recommends **{model['fact_table']}** as the fact table, see above."
        )

    error_kpis = [k for k in failed_kpis if k["status"] == "failed"]
    skipped_kpis = [k for k in failed_kpis if k["status"] == "skipped"]

    if error_kpis:
        st.subheader(f"{len(error_kpis)} KPI(s) failed to compute")
        for k in error_kpis:
            st.write(f"**{k['name']}**: {k.get('error', 'unknown error')}")
            st.code(k["sql"], language="sql")

    if skipped_kpis:
        st.subheader(f"{len(skipped_kpis)} KPI(s) computed but not shown")
        for k in skipped_kpis:
            st.write(f"**{k['name']}**: {k.get('error', 'not useful to show')}")
            st.code(k["sql"], language="sql")
