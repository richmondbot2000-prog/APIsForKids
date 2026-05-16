"""
One-off probe: find EVERY column across the seven Reporting* DBs that
could carry an author / actor identifier for a person, and report which
ones actually overlap with our staff list (from staff.json).

We're already pulling ClientUsername-based activity into
staff-activity-buckets.json. This probe looks for the *other* columns
that might also carry per-row authorship — CreatedBy, ModifiedBy,
SentBy, EnteredBy, Author, Operator, Agent, etc. — so we can widen
the bucket scanner.

Output:
- staff-activity-probe.json at the repo root with one row per
  (database, schema, table, column, ts_column) candidate, including:
    rows_sampled         — TOP 5000 rows scanned
    distinct_values      — distinct non-null values found
    matched_staff        — count of distinct staff usernames matched
    sample_matched_users — up to 5 example matches (lowercased)
    sample_other_values  — up to 5 non-matched values (so we can see
                            whether they're robot tags vs unknown ppl)
- Sorted by matched_staff desc so the most promising candidates float
  to the top of the log.

Required env vars: same as scan_staff_activity*.py.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import pyodbc


DATABASES = [
    "ReportingApplications",
    "ReportingBrokers",
    "ReportingCentralCrm",
    "ReportingCommunications",
    "ReportingLoanbook",
    "ReportingPayments",
    "Whitebox",
]

# Column-name patterns that signal "row is authored by a person".
# Matched against lowercased column names.
AUTHOR_COL_PATTERNS = [
    r"username",          # ClientUsername, AgentUsername, etc.
    r"createdby",         # CreatedBy / CreatedByUser
    r"modifiedby", r"updatedby", r"changedby", r"addedby", r"deletedby",
    r"sentby", r"receivedby", r"openedby", r"closedby", r"loggedby",
    r"enteredby", r"issuedby", r"approvedby", r"rejectedby",
    r"author", r"actor",
    r"^operator", r"operatorname",
    r"^agent", r"agentname", r"agentusername",
    r"loginusername", r"loginname",
    r"^owner", r"ownername",
    r"emailfrom", r"sentfrom",
    r"assignedto", r"assignedby",
    # View / read / access patterns — passive interactions worth
    # capturing if any table audits them.
    r"viewedby", r"openedby", r"readby", r"accessedby",
    r"lastviewedby", r"lastopenedby", r"lastreadby", r"lastaccessedby",
    r"firstviewedby", r"firstreadby",
]

# Column-name patterns that DEFINITELY aren't authors (e.g., customer
# fields, product owners, currency owners). Used as a denylist on top
# of the pattern hits.
DENY_PATTERNS = [
    r"^customer", r"customername", r"^client$",   # customer-side
    r"productowner", r"productname",
    r"^lender", r"lenderowner",
    r"currency", r"deviceowner", r"branchowner",
]

TS_DATA_TYPES = ('datetime', 'datetime2', 'datetimeoffset', 'smalldatetime', 'date')
TS_NAME_PREF = (
    "DateTimeUTC", "DateTimeUtc", "UTCTime", "UtcTime",
    "EventDateUTC", "CreatedDateUTC", "CreatedAtUTC",
    "EventDateTime", "DateTime", "EventDate", "Created", "CreatedAt",
    "ModifiedDateUTC", "ModifiedAtUTC", "ModifiedDate", "ModifiedAt",
    "InsertDateUTC", "InsertedAt", "Stamp", "Timestamp", "EventTime",
    "StatusTime", "ReceivedAt", "ReceivedUtc", "SentAt", "SentUtc",
)
QUERY_TIMEOUT = 240
SAMPLE_ROWS = 5000   # TOP per (table, column) — keep the probe cheap


def env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"error: {name} not set")
    return v


def conn_str(database: str) -> str:
    return (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server={env('FABRIC_SQL_ENDPOINT')},1433;"
        f"Database={database};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=20;"
        "Authentication=ActiveDirectoryServicePrincipal;"
        f"UID={env('FABRIC_CLIENT_ID')};"
        f"PWD={env('FABRIC_CLIENT_SECRET')};"
    )


def is_author_col(col_name: str) -> bool:
    n = col_name.lower()
    for d in DENY_PATTERNS:
        if re.search(d, n): return False
    for p in AUTHOR_COL_PATTERNS:
        if re.search(p, n): return True
    return False


def build_staff_identifiers() -> set[str]:
    """All lowercased ClientUsername-shape strings that could belong to
    a Workspace user — workspace email + local-part @ every known
    tenant domain + the bare local-part."""
    staff_path = Path("staff.json")
    if not staff_path.exists():
        sys.exit("staff.json missing — run scan_directory.py first")
    staff = json.loads(staff_path.read_text())
    domains = [
        "rgroup.co.uk", "letme.co.uk", "letme.com",
        "transformcredit.com", "togetherloans.com",
        "lendingmate.ca", "rapida.bg", "rapidamoney.pl",
        "clearloans.com.au", "fianceo.com",
        "tandolan.dk", "tandolaina.fi",
    ]
    s = set()
    for u in staff.get("users", []):
        email = (u.get("email") or "").strip().lower()
        if not email or "@" not in email:
            continue
        local = email.split("@")[0]
        s.add(email)
        s.add(local)
        for d in domains:
            s.add(f"{local}@{d}")
    return s


def probe_database(db: str, cutoff_str: str, staff_set: set[str]):
    print(f"# {db}", flush=True)
    out = []
    try:
        c = pyodbc.connect(conn_str(db), timeout=20)
        c.timeout = QUERY_TIMEOUT
        cur = c.cursor()
    except Exception as e:
        print(f"  ! connect failed: {e}", flush=True)
        return out

    try:
        cur.execute("""
            SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
        """)
        rows = cur.fetchall()
    except Exception as e:
        print(f"  ! schema fetch failed: {e}", flush=True)
        try: c.close()
        except: pass
        return out

    cols_by_table: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for s, t, col, dt in rows:
        cols_by_table[(s, t)].append((col, dt))

    for (s, t), cols in cols_by_table.items():
        # Find candidate author columns + a timestamp column for this
        # table (so we can scope the sample to the same 14-day window
        # the bucket scanner uses).
        author_cols = [c for (c, dt) in cols if is_author_col(c)]
        if not author_cols:
            continue
        ts_candidates = [c for (c, dt) in cols if dt in TS_DATA_TYPES]
        ts_col = next((p for p in TS_NAME_PREF if p in ts_candidates), None)
        if not ts_col and ts_candidates:
            ts_col = ts_candidates[0]

        for col in author_cols:
            try:
                where = f"WHERE [{ts_col}] >= ?" if ts_col else ""
                params = [cutoff_str] if ts_col else []
                q = (
                    f"SELECT TOP {SAMPLE_ROWS} LOWER([{col}]) AS v, COUNT_BIG(*) AS n "
                    f"FROM [{s}].[{t}] "
                    f"{where} "
                    f"GROUP BY LOWER([{col}])"
                )
                cur.execute(q, params)
                values = cur.fetchall()
            except Exception as e:
                # Many columns will fail (incompatible types, etc.) — skip
                # quietly and keep going.
                continue

            distinct_total = 0
            matched_users = set()
            non_matched = []  # (value, count) tuples
            total_rows = 0
            matched_rows = 0
            for v, n in values:
                if v is None or v == "":
                    continue
                vv = v.strip().lower() if isinstance(v, str) else str(v).strip().lower()
                if not vv: continue
                distinct_total += 1
                cnt = int(n or 0)
                total_rows += cnt
                if vv in staff_set:
                    matched_users.add(vv)
                    matched_rows += cnt
                else:
                    if len(non_matched) < 5:
                        non_matched.append((vv[:80], cnt))

            if not distinct_total:
                continue

            out.append({
                "database": db,
                "schema": s,
                "table": t,
                "column": col,
                "ts_column": ts_col,
                "distinct_values": distinct_total,
                "rows_in_window": total_rows,
                "matched_staff_count": len(matched_users),
                "matched_rows": matched_rows,
                "sample_matched_users": sorted(matched_users)[:5],
                "sample_other_values": non_matched,
            })

    try: c.close()
    except: pass
    return out


def main():
    started = datetime.datetime.now(datetime.timezone.utc)
    cutoff = started - datetime.timedelta(days=14)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    print(f"# probe_activity_columns start {started.isoformat()}  cutoff={cutoff.isoformat()}", flush=True)

    staff_set = build_staff_identifiers()
    print(f"# staff identifiers in scope: {len(staff_set)}", flush=True)

    all_rows = []
    for db in DATABASES:
        all_rows.extend(probe_database(db, cutoff_str, staff_set))

    # Sort: tables where the most staff members matched at the top.
    all_rows.sort(key=lambda r: (-(r["matched_staff_count"] or 0), -(r["matched_rows"] or 0)))

    payload = {
        "schema_version":      1,
        "snapshot_at":         started.isoformat(),
        "cutoff_utc":          cutoff.isoformat(),
        "staff_identifiers":   len(staff_set),
        "candidate_columns":   all_rows,
    }
    out_path = Path("staff-activity-probe.json").resolve()
    out_path.write_text(json.dumps(payload, indent=2))

    # Compact log summary.
    print(f"\n# === summary ({len(all_rows)} candidate columns) ===", flush=True)
    for r in all_rows[:80]:
        print(
            f"  [{r['matched_staff_count']:>3}] {r['database']}.{r['schema']}.{r['table']:<40} "
            f"col={r['column']:<28} ts={r['ts_column']:<22} rows={r['matched_rows']}/{r['rows_in_window']}",
            flush=True,
        )
    print(f"\n# wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
