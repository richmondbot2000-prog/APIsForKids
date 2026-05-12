#!/usr/bin/env python3
"""
One-off diagnostic. Two questions:

  1. How often is the same ARef purchased by multiple distinct brokers
     within the source-quality 60-day analysis window? Sizes the
     attribution bug in scan_source_quality.py (MAX(CampaignId)
     fallback is wrong when 2+ brokers sold the same customer).

  2. What table / column names in the warehouse look like the
     'backing tables' Kelly Black mentioned — pre-computed attribution
     of lead outcomes to the broker the lead was live with?

Reads Fabric warehouse with the same auth pattern as
scan_source_quality.py.
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

# Source / outcome / attribution / live / expiry keywords we'd
# expect Kelly's backing tables and the Lead Outcomes table to
# match.
TABLE_KEYWORDS = [
    "leadoutcome", "lead_outcome", "outcome",
    "leadattribution", "attribution",
    "leadresult", "leadhistory", "lead_history",
    "applicationhistory", "application_history",
    "leadlive", "lead_live", "leadexpiry", "expiry",
    "leadclaim", "claim",
]

COLUMN_KEYWORDS = [
    "leadoutcome", "outcomestatus", "outcome",
    "attribution", "attributedbroker", "attributedsource",
    "leadexpiry", "expirydate", "claimexpiry",
    "leadlive", "isliveat", "wasliveat",
    "buyingbroker", "winningbroker", "creditedsource",
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

    # ─── Q1: multi-broker ARef frequency ──────────────────────────
    print("=" * 78, flush=True)
    print("Q1: How often is the same ARef purchased by multiple brokers?", flush=True)
    print("=" * 78, flush=True)

    conn = pyodbc.connect(conn_str("ReportingApplications"), timeout=20)
    cur = conn.cursor()

    # We need a broker_id per lead. Lead has CampaignId; Campaign joins
    # to Source (the broker). Pull the campaign→broker map from
    # ReportingBrokers (loaded via separate connection below).
    cur.execute(
        """
        SELECT TOP 1 column_name
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE table_name = 'Leads' AND column_name IN ('ARef','CampaignId','LeadResultTypeId','DateReceivedUtc','LenderId')
        """
    )
    # Just ensure the table is reachable.

    # Pull the campaign→broker (SourceId) map.
    cmap: dict[int, int] = {}
    try:
        c2 = pyodbc.connect(conn_str("ReportingBrokers"), timeout=20)
        cur2 = c2.cursor()
        cur2.execute("SELECT CampaignId, SourceId FROM dbo.Campaigns")
        for cid, src in cur2.fetchall():
            if cid is None or src is None: continue
            cmap[int(cid)] = int(src)
        c2.close()
    except pyodbc.Error as e:
        print(f"# Campaign→broker map failed from ReportingBrokers: {e}", flush=True)
        # Fall back to local DB
        try:
            cur.execute("SELECT CampaignId, SourceId FROM dbo.Campaigns WHERE SourceId IS NOT NULL")
            for cid, src in cur.fetchall():
                if cid is None or src is None: continue
                cmap[int(cid)] = int(src)
        except Exception as e2:
            print(f"# Local fallback also failed: {e2}", flush=True)
    print(f"# Loaded {len(cmap):,} campaign→broker mappings", flush=True)

    # Pull purchased leads (ARef + CampaignId) over the window
    cur.execute(
        f"""
        SELECT l.ARef, l.CampaignId
        FROM dbo.Leads l
        WHERE l.DateReceivedUtc >= ? AND l.DateReceivedUtc < ?
          AND l.LenderId = ?
          AND l.LeadResultTypeId IN (1, 30)
          AND l.ARef IS NOT NULL
        """,
        [window_start, window_end, LENDER_ID],
    )

    aref_to_brokers: dict[str, set] = {}
    raw_lead_count = 0
    for aref, cid in cur.fetchall():
        if aref is None or cid is None: continue
        broker = cmap.get(int(cid))
        if broker is None: continue
        aref_to_brokers.setdefault(str(aref), set()).add(broker)
        raw_lead_count += 1

    total_arefs = len(aref_to_brokers)
    multi_arefs = {a: b for a, b in aref_to_brokers.items() if len(b) >= 2}
    pct_multi = (len(multi_arefs) / total_arefs * 100) if total_arefs else 0
    print(f"# Total purchased leads in window:  {raw_lead_count:,}", flush=True)
    print(f"# Distinct ARefs:                   {total_arefs:,}", flush=True)
    print(f"# ARefs bought by 2+ brokers:       {len(multi_arefs):,} ({pct_multi:.2f}%)", flush=True)
    if multi_arefs:
        from collections import Counter
        dist = Counter(len(b) for b in multi_arefs.values())
        print(f"#   distribution of broker count:", flush=True)
        for n in sorted(dist.keys()):
            print(f"#     {n} brokers: {dist[n]:,} ARefs", flush=True)

    # Of the multi-broker arefs, how many were PAID OUT? Worst-case
    # attribution error happens on paid loans (those move the cost
    # numbers).
    if multi_arefs:
        # Chunk into IN-lists to avoid parameter limit
        paid_multi = 0
        all_aref_set = set(multi_arefs.keys())
        sample = list(all_aref_set)[:50000]  # 50k arefs cap to keep query reasonable
        CHUNK = 1000
        for i in range(0, len(sample), CHUNK):
            chunk = sample[i:i+CHUNK]
            ph = ",".join(["?"] * len(chunk))
            cur.execute(
                f"""
                SELECT COUNT(*) FROM dbo.Applications a
                WHERE a.ARef IN ({ph})
                  AND a.LenderId = ?
                  AND a.ApplicationStatusTypeId = 5
                """,
                chunk + [LENDER_ID],
            )
            paid_multi += int(cur.fetchone()[0] or 0)
        pct_paid_multi = (paid_multi / len(sample) * 100) if sample else 0
        print(f"#   of those, paid out:            {paid_multi:,} ({pct_paid_multi:.2f}% of sampled multi-broker ARefs)", flush=True)

        # Also compute: % of all paid arefs that had multi-broker history
        cur.execute(
            f"""
            SELECT COUNT(DISTINCT a.ARef) FROM dbo.Applications a
            JOIN dbo.Leads l ON l.ARef = a.ARef
            WHERE l.DateReceivedUtc >= ? AND l.DateReceivedUtc < ?
              AND l.LenderId = ?
              AND l.LeadResultTypeId IN (1, 30)
              AND a.LenderId = ?
              AND a.ApplicationStatusTypeId = 5
            """,
            [window_start, window_end, LENDER_ID, LENDER_ID],
        )
        total_paid_arefs = int(cur.fetchone()[0] or 0)
        pct_of_paid = (paid_multi / total_paid_arefs * 100) if total_paid_arefs else 0
        print(f"#   total paid ARefs in window:    {total_paid_arefs:,}", flush=True)
        print(f"#   % of paid ARefs that were multi-broker: ~{pct_of_paid:.1f}% (based on sample)", flush=True)

    conn.close()

    # ─── Q2: candidate backing-table names ─────────────────────────
    print()
    print("=" * 78, flush=True)
    print("Q2: Candidate 'backing tables' — search INFORMATION_SCHEMA", flush=True)
    print("=" * 78, flush=True)

    for db in DBS_TO_SEARCH:
        try:
            c3 = pyodbc.connect(conn_str(db), timeout=20)
            cur3 = c3.cursor()
        except pyodbc.Error as e:
            print(f"# {db}: unreachable ({e})", flush=True)
            continue

        # Table-name matches
        try:
            cur3.execute(
                """
                SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
                FROM INFORMATION_SCHEMA.TABLES
                """
            )
            tables = cur3.fetchall()
            matched_tables = [
                (sch, name, t) for sch, name, t in tables
                if any(kw in name.lower() for kw in TABLE_KEYWORDS)
            ]
            if matched_tables:
                print(f"# {db} — tables matching keywords:", flush=True)
                for sch, name, t in matched_tables:
                    print(f"#   {sch}.{name}  [{t}]", flush=True)
        except Exception as e:
            print(f"# {db}: table search failed — {e}", flush=True)

        # Column-name matches
        try:
            cur3.execute(
                """
                SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                """
            )
            cols = cur3.fetchall()
            matched_cols = [
                (sch, tn, cn) for sch, tn, cn in cols
                if any(kw in cn.lower() for kw in COLUMN_KEYWORDS)
            ]
            if matched_cols:
                # Group by (sch.table) so we see related columns together
                from collections import defaultdict
                by_table = defaultdict(list)
                for sch, tn, cn in matched_cols:
                    by_table[f"{sch}.{tn}"].append(cn)
                print(f"# {db} — columns matching keywords:", flush=True)
                for tbl in sorted(by_table.keys()):
                    print(f"#   {tbl}: {', '.join(sorted(set(by_table[tbl])))}", flush=True)
        except Exception as e:
            print(f"# {db}: column search failed — {e}", flush=True)

        c3.close()

    print()
    print("# done.", flush=True)


if __name__ == "__main__":
    main()
