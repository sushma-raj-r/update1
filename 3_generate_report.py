"""
3_generate_report.py
────────────────────
Public Transit Authority — Delay Attribution Report Generator
Reads transport_data_processed.csv and writes Final_Attribution_Report.txt.

Dependencies: pandas (pip install pandas)
Usage:        python 3_generate_report.py
"""

import sys
from datetime import datetime
import pandas as pd


# ── Constants ─────────────────────────────────────────────────────────────────

INPUT_FILE  = "transport_data_processed.csv"
OUTPUT_FILE = "Final_Attribution_Report.txt"

REQUIRED_COLUMNS = ["Route_ID", "Stop_ID", "Delay_Cause"]
NORMAL_LABEL     = "Normal"


# ── Step 1: Load & Validate ───────────────────────────────────────────────────

def load_and_validate(filepath: str) -> pd.DataFrame:
    """Read the CSV and confirm every required column is present."""
    try:
        df = pd.read_csv(filepath, dtype=str)  # dtype=str keeps IDs as strings
    except FileNotFoundError:
        print(f"[ERROR] Input file not found: '{filepath}'")
        print("        Make sure transport_data_processed.csv is in the same folder.")
        sys.exit(1)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        print(f"[ERROR] Missing required column(s): {missing}")
        print(f"        Columns found in file: {list(df.columns)}")
        sys.exit(1)

    # Drop rows where any required column is blank
    df = df.dropna(subset=REQUIRED_COLUMNS)

    print(f"[OK] Loaded {len(df):,} records from '{filepath}'")
    return df


# ── Step 2: Overall Summary ───────────────────────────────────────────────────

def compute_overall_summary(df: pd.DataFrame) -> dict:
    """
    Returns:
        total_records   — total row count
        total_delayed   — rows where Delay_Cause != 'Normal'
        top_cause       — most frequent non-Normal cause (string)
        top_cause_count — how many times that cause appears
    """
    total_records = len(df)

    delayed_df    = df[df["Delay_Cause"] != NORMAL_LABEL]
    total_delayed = len(delayed_df)

    if total_delayed == 0:
        top_cause       = f"{NORMAL_LABEL} — No issues detected"
        top_cause_count = 0
    else:
        cause_counts    = delayed_df["Delay_Cause"].value_counts()
        top_cause       = cause_counts.idxmax()
        top_cause_count = cause_counts.max()

    return {
        "total_records":   total_records,
        "total_delayed":   total_delayed,
        "top_cause":       top_cause,
        "top_cause_count": top_cause_count,
    }


# ── Step 3: Route-Level Summary ───────────────────────────────────────────────

def compute_route_summaries(df: pd.DataFrame) -> list[dict]:
    """
    For every Route_ID, count each Delay_Cause and find the top non-Normal cause.
    Returns a list of dicts sorted by non-Normal delay count (descending).
    """
    summaries = []

    for route_id, route_df in df.groupby("Route_ID"):
        delayed_df    = route_df[route_df["Delay_Cause"] != NORMAL_LABEL]
        delayed_count = len(delayed_df)

        if delayed_count == 0:
            # All records for this route are Normal
            top_cause       = f"{NORMAL_LABEL} — No issues detected"
            top_cause_count = 0
            top_pct         = 0.0
        else:
            cause_counts    = delayed_df["Delay_Cause"].value_counts()
            top_cause       = cause_counts.idxmax()
            top_cause_count = cause_counts.max()
            # Percentage is relative to all non-Normal delays on this route
            top_pct         = (top_cause_count / delayed_count) * 100

        summaries.append({
            "route_id":       route_id,
            "delayed_count":  delayed_count,
            "top_cause":      top_cause,
            "top_cause_count": top_cause_count,
            "top_pct":        top_pct,
            "route_df":       route_df,   # kept for stop-level breakdown below
        })

    # Sort worst routes first (most non-Normal delays at the top)
    summaries.sort(key=lambda r: r["delayed_count"], reverse=True)
    return summaries


# ── Step 4: Stop-Level Breakdown ──────────────────────────────────────────────

def compute_stop_breakdown(route_df: pd.DataFrame) -> list[tuple]:
    """
    For one route's DataFrame, find stops that have at least one non-Normal delay.
    Returns a list of (stop_id, cause_summary_string) sorted by total delay count desc.

    cause_summary_string looks like:  "Route Congestion Pattern x3, Excessive Stop Dwell Time x1"
    """
    delayed_df = route_df[route_df["Delay_Cause"] != NORMAL_LABEL]

    if delayed_df.empty:
        return []

    results = []

    # Group by stop, then count each cause within that stop
    for stop_id, stop_df in delayed_df.groupby("Stop_ID"):
        cause_counts = (
            stop_df["Delay_Cause"]
            .value_counts()                      # most frequent first
            .reset_index()
        )
        cause_counts.columns = ["cause", "count"]

        # Build the inline cause summary: "Cause A x3, Cause B x1"
        parts = [
            f"{row['cause']} x{row['count']}"
            for _, row in cause_counts.iterrows()
        ]
        cause_summary = ", ".join(parts)
        total_at_stop = len(stop_df)

        results.append((stop_id, cause_summary, total_at_stop))

    # Sort stops by total delay count, highest first
    results.sort(key=lambda x: x[2], reverse=True)

    # Return only (stop_id, cause_summary) — total was only needed for sorting
    return [(stop_id, summary) for stop_id, summary, _ in results]


# ── Step 5: Assemble Report Text ──────────────────────────────────────────────

def build_report(overall: dict, route_summaries: list[dict], timestamp: str) -> str:
    """Assemble all sections into the final report string."""

    total_records = overall["total_records"]
    total_delayed = overall["total_delayed"]
    delayed_pct   = (total_delayed / total_records * 100) if total_records else 0

    lines = []

    # ── Header ────────────────────────────────────────────────────────────────
    lines += [
        "============================================",
        " TRANSIT DELAY ATTRIBUTION REPORT",
        f" Generated: {timestamp}",
        f" Source: {INPUT_FILE}",
        f" Total Records Analyzed: {total_records:,}",
        "============================================",
        "",
    ]

    # ── Executive Summary ─────────────────────────────────────────────────────
    lines += [
        "EXECUTIVE SUMMARY",
        "------------------",
        f"Total Delayed Records: {total_delayed:,} out of {total_records:,} ({delayed_pct:.1f}%)",
        f"Most Common System-Wide Delay Cause: {overall['top_cause']} ({overall['top_cause_count']:,} occurrences)",
        "",
    ]

    # ── Route-by-Route Breakdown ──────────────────────────────────────────────
    lines += [
        "ROUTE-BY-ROUTE BREAKDOWN",
        "-------------------------",
    ]

    for route in route_summaries:
        route_id   = route["route_id"]
        top_cause  = route["top_cause"]
        top_count  = route["top_cause_count"]
        top_pct    = route["top_pct"]
        route_df   = route["route_df"]

        lines.append(f"Route: {route_id}")

        # Top cause line — format differs when there are no issues
        if route["delayed_count"] == 0:
            lines.append(f"  Top Delay Cause: {top_cause}")
        else:
            lines.append(
                f"  Top Delay Cause: {top_cause} "
                f"({top_count} occurrences, {top_pct:.1f}% of this route's delays)"
            )

        # Problem stops
        stop_breakdown = compute_stop_breakdown(route_df)

        if stop_breakdown:
            lines.append("  Problem Stops:")
            for stop_id, cause_summary in stop_breakdown:
                lines.append(f"    - {stop_id}: {cause_summary}")
        else:
            lines.append("  Problem Stops: None")

        lines.append("")   # blank line between routes

    # ── Footer ────────────────────────────────────────────────────────────────
    lines += [
        "============================================",
        " END OF REPORT",
        "============================================",
    ]

    return "\n".join(lines)


# ── Step 6: Save Report ───────────────────────────────────────────────────────

def save_report(text: str, filepath: str) -> None:
    """Write the final report string to a .txt file (UTF-8)."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Load and validate input
    df = load_and_validate(INPUT_FILE)

    # 2. Compute all three levels of analysis
    overall         = compute_overall_summary(df)
    route_summaries = compute_route_summaries(df)

    # 3. Build and save the report
    report_text = build_report(overall, route_summaries, timestamp)
    save_report(report_text, OUTPUT_FILE)

    # 4. Console confirmation
    route_count = len(route_summaries)
    print(f"Report saved to {OUTPUT_FILE} ({route_count} routes analyzed).")


if __name__ == "__main__":
    main()