#!/usr/bin/env python3
"""
Schema probe for the lead-outcomes tables identified by
probe_lead_attribution.py. Three things:

  1. Full column list + 5-row sample + row count for
     ReportingApplications.dbo.LeadOutcomes.
  2. Full content of ReportingApplications.dbo.LeadOutcomeTypes
     (the outcome-status enum).
  3. Search every reporting DB's INFORMATION_SCHEMA.VIEWS for views
     whose name hints at pre-computed lead attribution / live periods.

  Bonus: distribution of LeadOutcomeTypeID across the 60d source-
  quality window so we can see what the actual outcomes look like.

Run via: gh workflow run probe-lead-outcomes.yml --ref main
"""
from __future__ import annotations

import os
import datetime
import pyodbc

FABRIC_SQL_ENDPOINT = os.environ["FABRIC_SQL_ENDPOINT"]
FABRIC_TENANT_ID    = os.environ["FABRIC_TENANT_ID"]
FABRIC_CLIENT_ID    = os.environ["FABRIC_CLIENT_ID"]
FABRIC_CLIENT_SECRET = os.environ["FABRIC_CLIENT_SECRET"]

WINDOW_DAYS     = int(os.environ.get("SQ_WINDOW_DAYS", "60"))
MATURATION_DAYS = int(os.environ.get("SQ_MATURATION_DAYS", "30"))
LENDER_ID       = int(os.environ.get("SQ_LENDER_ID", "6"))

DBS_TO_SEARCH = [
    "ReportingApplications",
    "ReportingBrokers",
    "ReportingCentralCrm",
    "ReportingLoanbook",
    "ReportingTracking",
    "ReportingPayments",
    "Whitebox",
]

# Keywords for view-name search.
VIEW_KEYWORDS = [
    "leadattribution", "leadresult", "leadoutcome", "leadlive",
    "leadclaim", "leadhistory", "lead_history", "attribution",
    "outcomeattribution", "buyingbroker", "creditedsource",
    "applicationhistory", "application_history",
    "applicationoutcome", "applicationresult",
]


def conn_str(database: str) -> str:
    return (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server={FABRIC_SQL_ENDPOINT},1433;"
        f"Database={database};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        "Authentication=ActiveDirectoryServicePrincipal;"
        f"UID={FABRIC_CLIENT_ID};PWD={FABRIC_CLIENT_SECRET};"
        f"Authority Id={FABRIC_TENANT_ID};"
    )


def main() -> None:
    started = datetime.datetime.now(datetime.timezone.utc)
    window_end   = started - datetime.timedelta(days=MATURATION_DAYS)
    window_start = window_end - datetime.timedelta(days=WINDOW_DAYS)
    print(f"# Window: {window_start.date()} → {window_end.date()} ({WINDOW_DAYS}d ending {MATURATION_DAYS}d ago)", flush=True)
    print(f"# Lender: {LENDER_ID}", flush=True)
    print()

    conn = pyodbc.connect(conn_str("ReportingApplications"), timeout=20)
    cur = conn.cursor()

    # ─── Schema of dbo.LeadOutcomes ─────────────────────────────────
    print("=" * 78, flush=True)
    print("dbo.LeadOutcomes — columns:", flush=True)
    print("=" * 78, flush=True)
    cur.execute(
        """
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'LeadOutcomes'
        ORDER BY ORDINAL_POSITION
        """
    )
    leadoutcome_cols = []
    for col_name, data_type, nullable, max_len in cur.fetchall():
        leadoutcome_cols.append(col_name)
        size = f"({max_len})" if max_len else ""
        print(f"  {col_name:<36} {data_type}{size}  {'NULL' if nullable == 'YES' else 'NOT NULL'}", flush=True)

    # Row count
    try:
        cur.execute("SELECT COUNT_BIG(*) FROM dbo.LeadOutcomes")
        total = cur.fetchone()[0]
        print(f"\n# Total rows in dbo.LeadOutcomes: {total:,}", flush=True)
    except Exception as e:
        print(f"# COUNT failed: {e}", flush=True)

    # Sample rows
    print()
    print("# Sample rows (TOP 5):", flush=True)
    sel_cols = ", ".join(f"[{c}]" for c in leadoutcome_cols)
    cur.execute(f"SELECT TOP 5 {sel_cols} FROM dbo.LeadOutcomes")
    for row in cur.fetchall():
        for col, val in zip(leadoutcome_cols, row):
            v = str(val) if val is not None else "NULL"
            if len(v) > 80: v = v[:77] + "..."
            print(f"    {col}: {v}", flush=True)
        print("    ---", flush=True)

    # Recent rows — outcomes in the source-quality window
    print()
    print("# Recent rows (TOP 5 ordered by most recent date column):", flush=True)
    # Pick a date column if available
    date_cols = [c for c in leadoutcome_cols if 'date' in c.lower() or 'time' in c.lower() or 'utc' in c.lower()]
    if date_cols:
        date_col = date_cols[0]
        try:
            cur.execute(f"SELECT TOP 5 {sel_cols} FROM dbo.LeadOutcomes ORDER BY [{date_col}] DESC")
            for row in cur.fetchall():
                parts = [f"{c}={v!r}" for c, v in zip(leadoutcome_cols, row) if v is not None]
                print(f"    {' | '.join(parts[:8])}", flush=True)
        except Exception as e:
            print(f"# date-sort failed on {date_col}: {e}", flush=True)

    # ─── Schema + content of dbo.LeadOutcomeTypes ───────────────────
    print()
    print("=" * 78, flush=True)
    print("dbo.LeadOutcomeTypes — columns + full content:", flush=True)
    print("=" * 78, flush=True)
    cur.execute(
        """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'LeadOutcomeTypes'
        ORDER BY ORDINAL_POSITION
        """
    )
    lot_cols = []
    for col_name, data_type in cur.fetchall():
        lot_cols.append(col_name)
        print(f"  {col_name:<36} {data_type}", flush=True)

    if lot_cols:
        sel = ", ".join(f"[{c}]" for c in lot_cols)
        cur.execute(f"SELECT {sel} FROM dbo.LeadOutcomeTypes ORDER BY 1")
        print()
        print(f"  {' | '.join(lot_cols)}", flush=True)
        for row in cur.fetchall():
            print(f"  {' | '.join(str(v) if v is not None else 'NULL' for v in row)}", flush=True)

    # ─── Distribution of outcome types in our window ────────────────
    print()
    print("=" * 78, flush=True)
    print("LeadOutcome distribution within the source-quality window:", flush=True)
    print("=" * 78, flush=True)
    # Find the date column on LeadOutcomes and the type column
    type_col = next((c for c in leadoutcome_cols if 'type' in c.lower() and 'id' in c.lower()), None)
    date_col = next((c for c in leadoutcome_cols if 'date' in c.lower() and ('utc' in c.lower() or 'created' in c.lower())), None)
    if type_col and date_col:
        try:
            cur.execute(
                f"""
                SELECT lo.[{type_col}] AS tid, lt.LeadOutcomeTypeDescription, COUNT(*) AS n
                FROM dbo.LeadOutcomes lo
                LEFT JOIN dbo.LeadOutcomeTypes lt ON lt.LeadOutcomeTypeId = lo.[{type_col}]
                WHERE lo.[{date_col}] >= ? AND lo.[{date_col}] < ?
                GROUP BY lo.[{type_col}], lt.LeadOutcomeTypeDescription
                ORDER BY n DESC
                """,
                [window_start, window_end],
            )
            for tid, desc, n in cur.fetchall():
                desc_str = desc if desc else "(no description)"
                print(f"  {tid!r:<6} {desc_str[:50]:<52} {n:>12,}", flush=True)
        except Exception as e:
            print(f"# Distribution query failed: {e}", flush=True)
    else:
        print(f"# Couldn't find type / date columns. type_col={type_col} date_col={date_col}", flush=True)

    # ─── Application History table presence check ───────────────────
    print()
    print("=" * 78, flush=True)
    print("ApplicationHistory presence check:", flush=True)
    print("=" * 78, flush=True)
    cur.execute(
        """
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME LIKE '%History%' OR TABLE_NAME LIKE '%history%'
        """
    )
    for sch, tn in cur.fetchall():
        print(f"  {sch}.{tn}", flush=True)
        try:
            cur.execute(
                f"""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = '{sch}' AND TABLE_NAME = '{tn}'
                ORDER BY ORDINAL_POSITION
                """
            )
            for col_name, data_type in cur.fetchall():
                print(f"    {col_name:<36} {data_type}", flush=True)
        except Exception as e:
            print(f"    (columns query failed: {e})", flush=True)

    conn.close()

    # ─── View search across all reporting DBs ────────────────────────
    print()
    print("=" * 78, flush=True)
    print("View search (INFORMATION_SCHEMA.VIEWS) across all reporting DBs:", flush=True)
    print("=" * 78, flush=True)
    for db in DBS_TO_SEARCH:
        try:
            c3 = pyodbc.connect(conn_str(db), timeout=20)
            cur3 = c3.cursor()
        except pyodbc.Error as e:
            print(f"# {db}: unreachable ({e})", flush=True)
            continue

        try:
            cur3.execute(
                """
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM INFORMATION_SCHEMA.VIEWS
                """
            )
            views = cur3.fetchall()
            matched = [(sch, name) for sch, name in views
                       if any(kw in name.lower() for kw in VIEW_KEYWORDS)]
            if matched:
                print(f"# {db} — views matching keywords:", flush=True)
                for sch, name in matched:
                    print(f"#   {sch}.{name}", flush=True)
            elif views:
                # Also dump ALL view names (capped at 50) so we can spot
                # anything we missed via keyword.
                print(f"# {db} — total views: {len(views)}. First 50:", flush=True)
                for sch, name in views[:50]:
                    print(f"#   {sch}.{name}", flush=True)
            else:
                print(f"# {db} — no views.", flush=True)
        except Exception as e:
            print(f"# {db}: view search failed — {e}", flush=True)

        c3.close()

    print()
    print("# done.", flush=True)


if __name__ == "__main__":
    main()
