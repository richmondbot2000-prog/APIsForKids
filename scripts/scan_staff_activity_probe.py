"""
One-off probe: find every table with a ClientUsername column across the
reporting warehouses and sample the most-active distinct usernames per DB.

We don't yet know whether the warehouse logs writes as `name@rgroup.co.uk`
(old domain), `name@letme.co.uk` (current Workspace), or some other format.
This script answers that question by listing the top 50 distinct usernames
per database with their write counts and most-recent activity.

Output: staff-activity-probe.json at repo root.

Required env vars (same set as scan_row_counts.py):
  FABRIC_SQL_ENDPOINT, FABRIC_TENANT_ID, FABRIC_CLIENT_ID, FABRIC_CLIENT_SECRET
"""
from __future__ import annotations

import datetime
import json
import os
import sys
from pathlib import Path

import pyodbc

DATABASES = [
    "ReportingApplications",
    "ReportingBrokers",
    "ReportingCentralCrm",
    "ReportingCommunications",
    "ReportingCreditbuilder",
    "ReportingLoanbook",
    "ReportingLookup",
    "ReportingPayments",
    "ReportingTracking",
    "Whitebox",
]

QUERY_TIMEOUT = 120
TOP_PER_DB = 50


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
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=15;"
        "Authentication=ActiveDirectoryServicePrincipal;"
        f"UID={env('FABRIC_CLIENT_ID')};"
        f"PWD={env('FABRIC_CLIENT_SECRET')};"
    )


def probe_database(database: str) -> dict:
    print(f"# {database}", flush=True)
    out = {"database": database, "tables_with_clientusername": [], "top_users": [], "error": None}
    try:
        c = pyodbc.connect(conn_str(database), timeout=15)
        c.timeout = QUERY_TIMEOUT
        cur = c.cursor()
    except Exception as e:
        out["error"] = f"connect failed: {e}"
        return out

    try:
        cur.execute("""
            SELECT TABLE_SCHEMA, TABLE_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE COLUMN_NAME = 'ClientUsername'
            ORDER BY TABLE_SCHEMA, TABLE_NAME
        """)
        tables = [(r[0], r[1]) for r in cur.fetchall()]
        out["tables_with_clientusername"] = [f"{s}.{t}" for s, t in tables]
        if not tables:
            return out

        # Pick the largest table (likely an Events table) and sample top users from it.
        # We try each table until one returns rows quickly.
        for schema, table in tables:
            try:
                q = f"""
                    SELECT TOP {TOP_PER_DB}
                        ClientUsername,
                        COUNT(*) AS write_count
                    FROM [{schema}].[{table}]
                    WHERE ClientUsername IS NOT NULL
                    GROUP BY ClientUsername
                    ORDER BY write_count DESC
                """
                cur.execute(q)
                rows = cur.fetchall()
                if rows:
                    out["top_users"] = [
                        {"username": r[0], "writes": r[1], "from_table": f"{schema}.{table}"}
                        for r in rows
                    ]
                    break  # first non-empty table is enough for a probe
            except Exception as e:
                # Table might not be queryable for the SP — skip and continue
                print(f"  ! {schema}.{table}: {e}", flush=True)
                continue
    except Exception as e:
        out["error"] = f"query failed: {e}"
    finally:
        try:
            c.close()
        except Exception:
            pass
    return out


def main() -> None:
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"# probe start {started}", flush=True)
    by_db = []
    for db in DATABASES:
        by_db.append(probe_database(db))

    output = {
        "snapshot_at": started,
        "databases": by_db,
    }
    out_path = Path("staff-activity-probe.json")
    out_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"# wrote {out_path} ({out_path.stat().st_size} bytes)", flush=True)


if __name__ == "__main__":
    main()
