"""
Scan the Fabric warehouse for monthly Top-Up Eligibility data.

Output: `topups.json` at repo root, used by `topups.html` to render a 24-month
chart of:
  - live_loans     — distinct LoanbookIds with any LoanHistory entry that month
  - tue_eligible   — distinct LoanbookIds with at least one LoanHistory entry
                     where TueStatus=1 in that month

Source: `ReportingLoanbook.dbo.Loan_History` (~197M rows; snapshots per live
loan per day, plus one row per transaction). The query buckets by month over
the last 24 calendar months (UTC), grouping per LoanbookId so each loan
counts once per month regardless of how many snapshots it has.

Required env vars (same as scan_row_counts.py):
  FABRIC_SQL_ENDPOINT, FABRIC_TENANT_ID, FABRIC_CLIENT_ID, FABRIC_CLIENT_SECRET
"""
from __future__ import annotations

import datetime
import json
import os
import sys
from pathlib import Path

import pyodbc

DATABASE = "ReportingLoanbook"
TABLE_SCHEMA = "dbo"
TABLE_NAME = "Loan_History"

# Filter to a single lender — Transform Credit / Together Loans (USA) per the
# wiki's canonical lender mapping. Set to None to scan all lenders.
LENDER_ID = 6
LENDER_LABEL = "Transform Credit (LenderId 6, USA)"

# Months back from today's first-of-month. 24 = include the 24 most recent
# calendar months (the current month is partial).
WINDOW_MONTHS = 24

# Datetime SQL types we'll accept for the "when did this snapshot happen" column.
TS_DATA_TYPES = ('datetime', 'datetime2', 'datetimeoffset', 'smalldatetime', 'date')

# Preference order — pick the most semantically "happened-at" name available.
TS_NAME_PREF = (
    "DateTUtc", "DateTimeUtc", "DateTimeUTC",
    "DateTLocal", "DateTimeLocal",
    "EventDateUTC", "CreatedDateUTC", "CreatedAtUTC", "ModifiedDateUTC",
    "TimestampUTC", "InsertDateUTC",
)

QUERY_TIMEOUT = 600


def env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"error: {name} not set")
    return v


def conn_str() -> str:
    return (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server={env('FABRIC_SQL_ENDPOINT')},1433;"
        f"Database={DATABASE};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=20;"
        "Authentication=ActiveDirectoryServicePrincipal;"
        f"UID={env('FABRIC_CLIENT_ID')};"
        f"PWD={env('FABRIC_CLIENT_SECRET')};"
    )


def discover_threshold_columns(cur, table: str) -> dict:
    """The wiki uses TUEMaxBalance / TUE_MaxBalance / TUEArrearsPosition /
    TUE_ArrearsPosition / TUEDaysOld interchangeably depending on schema
    vintage. Find what's actually present on the given table.
    """
    cur.execute(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        """,
        [TABLE_SCHEMA, table],
    )
    cols = {c[0] for c in cur.fetchall()}
    def pick(*candidates):
        return next((c for c in candidates if c in cols), None)
    return {
        "max_balance":      pick("TUEMaxBalance", "TUE_MaxBalance"),
        "arrears_position": pick("TUEArrearsPosition", "TUE_ArrearsPosition"),
        "days_old":         pick("TUEDaysOld", "TUE_DaysOld"),
    }


def fetch_lender_thresholds(cur, lender_table: str) -> dict | None:
    """Read the per-loan TUE thresholds for our target lender, find the
    distribution. Returns {primary: {…}, variations: [{…count}], distinct: int}.
    Returns None if any required column is missing on the table.
    """
    cols = discover_threshold_columns(cur, lender_table)
    missing = [k for k, v in cols.items() if not v]
    if missing:
        print(f"# threshold columns missing on {lender_table}: {missing}", flush=True)
        return None
    print(f"# threshold columns on {lender_table}: {cols}", flush=True)

    q = f"""
        SELECT
            [{cols['max_balance']}]      AS max_balance,
            [{cols['arrears_position']}] AS arrears_position,
            [{cols['days_old']}]         AS days_old,
            COUNT(*) AS loan_count
        FROM [{TABLE_SCHEMA}].[{lender_table}]
        WHERE LenderId = ?
        GROUP BY [{cols['max_balance']}], [{cols['arrears_position']}], [{cols['days_old']}]
        ORDER BY loan_count DESC
    """
    cur.execute(q, [LENDER_ID])
    rows = [
        {
            "max_balance":      float(r[0]) if r[0] is not None else None,
            "arrears_position": float(r[1]) if r[1] is not None else None,
            "days_old":         int(r[2])   if r[2] is not None else None,
            "loan_count":       int(r[3]),
        }
        for r in cur.fetchall()
    ]
    if not rows:
        return None
    return {
        "primary":   rows[0],   # most-common combination
        "variations": rows,
        "distinct":  len(rows),
        "source":    f"{TABLE_SCHEMA}.{lender_table}",
        "columns":   cols,
    }


def discover_lender_table(cur) -> str | None:
    """Find a table in this DB that has both LoanbookId AND LenderId columns,
    so we can JOIN against it to filter Loan_History to a single lender. We
    prefer the smallest such table to keep the join cheap."""
    cur.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE COLUMN_NAME IN ('LoanbookId', 'LenderId')
        GROUP BY TABLE_NAME
        HAVING COUNT(DISTINCT COLUMN_NAME) = 2
    """)
    candidates = [r[0] for r in cur.fetchall()]
    if not candidates:
        return None
    # Prefer smaller tables — quicker to scan in the inner CTE.
    sized = []
    for t in candidates:
        try:
            cur.execute(f"SELECT COUNT_BIG(*) FROM [{TABLE_SCHEMA}].[{t}]")
            sized.append((cur.fetchone()[0], t))
        except Exception:
            sized.append((10**18, t))
    sized.sort()
    chosen = sized[0][1]
    print(f"# lender-mapping table: {chosen}  (candidates ranked by size: {[(t, n) for n, t in sized]})", flush=True)
    return chosen


def discover_timestamp_column(cur) -> str:
    """Find the best timestamp column on Loan_History via INFORMATION_SCHEMA."""
    placeholders = ",".join(["?"] * len(TS_DATA_TYPES))
    cur.execute(
        f"""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
          AND DATA_TYPE IN ({placeholders})
        """,
        [TABLE_SCHEMA, TABLE_NAME, *TS_DATA_TYPES],
    )
    cols = [c for c, _ in cur.fetchall()]
    if not cols:
        sys.exit(f"error: no datetime-typed columns found on {TABLE_SCHEMA}.{TABLE_NAME}")
    chosen = next((p for p in TS_NAME_PREF if p in cols), cols[0])
    print(f"# timestamp column: {chosen}  (other datetime cols here: {[c for c in cols if c != chosen]})", flush=True)
    return chosen


def main() -> None:
    started = datetime.datetime.now(datetime.timezone.utc)
    today = started.date()
    # Earliest month we want is (today.year/month - WINDOW_MONTHS + 1)'s 1st.
    # We compute it by stepping back month-by-month so calendar arithmetic
    # behaves correctly across year boundaries.
    y, m = today.year, today.month
    for _ in range(WINDOW_MONTHS - 1):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    cutoff = datetime.date(y, m, 1)
    print(f"# scan_topups start {started.isoformat()}  cutoff={cutoff}  window={WINDOW_MONTHS} months", flush=True)

    c = pyodbc.connect(conn_str(), timeout=20)
    c.timeout = QUERY_TIMEOUT
    cur = c.cursor()
    ts = discover_timestamp_column(cur)

    # `LenderId` lives on whichever loan-state table happens to have it. We
    # auto-discover the right table rather than hard-coding (it varies by
    # warehouse vintage). We pre-filter LoanbookIds in a CTE then aggregate
    # snapshots — keeps the join cheap on the 197M-row source.
    lender_table = discover_lender_table(cur) if LENDER_ID is not None else None
    if LENDER_ID is not None:
        if not lender_table:
            sys.exit(f"error: no table in {DATABASE}.{TABLE_SCHEMA}.* has both LoanbookId AND LenderId columns")
        q = f"""
            WITH lender_loans AS (
                SELECT DISTINCT LoanbookId
                FROM [{TABLE_SCHEMA}].[{lender_table}]
                WHERE LenderId = ?
            ),
            per_loan_month AS (
                SELECT
                    DATEFROMPARTS(YEAR(lh.[{ts}]), MONTH(lh.[{ts}]), 1) AS month_start,
                    lh.LoanbookId,
                    MAX(CASE WHEN lh.TueStatus = 1 THEN 1 ELSE 0 END) AS was_tue
                FROM [{TABLE_SCHEMA}].[{TABLE_NAME}] lh
                INNER JOIN lender_loans ll ON ll.LoanbookId = lh.LoanbookId
                WHERE lh.[{ts}] >= ?
                  AND lh.LoanbookId IS NOT NULL
                GROUP BY DATEFROMPARTS(YEAR(lh.[{ts}]), MONTH(lh.[{ts}]), 1), lh.LoanbookId
            )
            SELECT month_start, COUNT(*) AS live_loans, SUM(was_tue) AS tue_eligible
            FROM per_loan_month
            GROUP BY month_start
            ORDER BY month_start;
        """
        params = [LENDER_ID, cutoff]
    else:
        q = f"""
            WITH per_loan_month AS (
                SELECT
                    DATEFROMPARTS(YEAR([{ts}]), MONTH([{ts}]), 1) AS month_start,
                    LoanbookId,
                    MAX(CASE WHEN TueStatus = 1 THEN 1 ELSE 0 END) AS was_tue
                FROM [{TABLE_SCHEMA}].[{TABLE_NAME}]
                WHERE [{ts}] >= ?
                  AND LoanbookId IS NOT NULL
                GROUP BY DATEFROMPARTS(YEAR([{ts}]), MONTH([{ts}]), 1), LoanbookId
            )
            SELECT month_start, COUNT(*) AS live_loans, SUM(was_tue) AS tue_eligible
            FROM per_loan_month
            GROUP BY month_start
            ORDER BY month_start;
        """
        params = [cutoff]
    print(f"# running aggregation query…  lender filter: {LENDER_LABEL if LENDER_ID is not None else 'NONE (all lenders)'}", flush=True)
    cur.execute(q, params)
    rows = [(r[0], int(r[1]), int(r[2])) for r in cur.fetchall()]
    print(f"# returned {len(rows)} month rows", flush=True)
    try:
        c.close()
    except Exception:
        pass

    # Build the output: ensure every month in the window is present (zeros if
    # absent) so the chart's x-axis is dense.
    by_month = {(r[0].year, r[0].month): r for r in rows}
    series = []
    y, m = cutoff.year, cutoff.month
    for _ in range(WINDOW_MONTHS):
        bucket = by_month.get((y, m))
        if bucket:
            _, live, tue = bucket
        else:
            live, tue = 0, 0
        series.append({
            "month": f"{y:04d}-{m:02d}",
            "live_loans": live,
            "tue_eligible": tue,
        })
        m += 1
        if m == 13:
            m = 1
            y += 1

    # Totals across the window — useful headline numbers.
    total_live = sum(s["live_loans"] for s in series)
    total_tue = sum(s["tue_eligible"] for s in series)

    # Pull this lender's actual TUE thresholds. Try the lender_table we already
    # found; if it doesn't have the threshold columns, fall back to
    # LoanAtInception (which the wiki says owns them).
    lender_thresholds = None
    if LENDER_ID is not None:
        if lender_table:
            lender_thresholds = fetch_lender_thresholds(cur, lender_table)
        if lender_thresholds is None and lender_table != "LoanAtInception":
            try:
                lender_thresholds = fetch_lender_thresholds(cur, "LoanAtInception")
            except Exception as e:
                print(f"# threshold fallback failed: {e}", flush=True)

    output = {
        "snapshot_at": started.isoformat(),
        "snapshot_date": today.isoformat(),
        "window_months": WINDOW_MONTHS,
        "cutoff_month": cutoff.isoformat(),
        "source_table": f"{DATABASE}.{TABLE_SCHEMA}.{TABLE_NAME}",
        "timestamp_column": ts,
        "lender_id": LENDER_ID,
        "lender_label": LENDER_LABEL,
        "lender_thresholds": lender_thresholds,
        "totals": {
            "live_loans_loan_months":   total_live,   # SUM, not distinct
            "tue_eligible_loan_months": total_tue,
        },
        "series": series,
    }
    out_path = Path("topups.json")
    out_path.write_text(json.dumps(output, indent=2))
    print(f"# wrote {out_path} ({out_path.stat().st_size} bytes); months={len(series)} totals live={total_live} tue={total_tue}", flush=True)


if __name__ == "__main__":
    main()
