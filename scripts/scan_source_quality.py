"""
Source-quality analysis for the Brokers page.

Two outputs over a rolling 60-day window:

A) **Weak accepted sources** — sources we currently buy leads from whose
   funnel-to-paid-out rate is statistically below the cohort median.
   Volume-gated so a 3-purchased-leads source can't dominate the list.

B) **Blocked sources to reconsider** — sources whose leads get
   LeadResultTypeId = -1 ("Source excluded") in the window. For each
   excluded person we look for an identity match in our purchased leads
   from OTHER sources in the same window. Match logic:

       SSN/GovernmentIdNumber match
     OR (PhoneNumber AND DateOfBirth) match
     OR (EmailAddress  AND DateOfBirth) match

   If a meaningful share of an excluded source's people later showed
   up under another source and paid out, that source's audience is
   actually decent — worth reconsidering the block.

Output: `source-quality.json` at repo root.

Required env vars (same set as scan_brokers.py):
  FABRIC_SQL_ENDPOINT, FABRIC_TENANT_ID, FABRIC_CLIENT_ID, FABRIC_CLIENT_SECRET

Optional:
  SQ_WINDOW_DAYS    rolling window (default 60)
  SQ_LENDER_ID      LenderId to score (default 6 = Transform Credit)
  SQ_MIN_VOLUME     min purchased leads for a source to qualify for
                    the weak-accepted ranking (default 200)
  SQ_MIN_EXCLUDED   min source-excluded leads for a source to appear
                    in the blocked-to-reconsider list (default 200)
"""
from __future__ import annotations

import datetime
import json
import os
import statistics
import sys
from pathlib import Path

import pyodbc

LENDER_ID = int(os.environ.get("SQ_LENDER_ID", "6"))
LENDER_LABEL = "Transform Credit (LenderId 6, USA)" if LENDER_ID == 6 else f"LenderId {LENDER_ID}"
WINDOW_DAYS = int(os.environ.get("SQ_WINDOW_DAYS", "60"))
MIN_VOLUME = int(os.environ.get("SQ_MIN_VOLUME", "200"))
MIN_EXCLUDED = int(os.environ.get("SQ_MIN_EXCLUDED", "200"))
QUERY_TIMEOUT = 1200   # identity-match join is heavy — allow up to 20 min

PURCHASED_RESULT_IDS = (1, 30)
EXCLUDED_RESULT_ID = -1


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


def discover_columns(cur, table: str, schema: str = "dbo") -> set[str]:
    cur.execute(
        """
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        """,
        [schema, table],
    )
    return {r[0] for r in cur.fetchall()}


def pick(cols: set[str], *candidates: str) -> str | None:
    return next((c for c in candidates if c in cols), None)


def main() -> None:
    started = datetime.datetime.now(datetime.timezone.utc)
    window_end = started
    window_start = started - datetime.timedelta(days=WINDOW_DAYS)
    print(
        f"# scan_source_quality start {started.isoformat()}  "
        f"window: {window_start.date()} → {window_end.date()} ({WINDOW_DAYS}d)  "
        f"lender: {LENDER_ID}  min_volume: {MIN_VOLUME}  min_excluded: {MIN_EXCLUDED}",
        flush=True,
    )

    conn = pyodbc.connect(conn_str("ReportingApplications"), timeout=20)
    conn.timeout = QUERY_TIMEOUT
    cur = conn.cursor()

    # ─── Discover columns ─────────────────────────────────────────────
    leads_cols = discover_columns(cur, "Leads")
    apps_cols = discover_columns(cur, "Applications")
    tasks_cols = discover_columns(cur, "Tasks")

    L_aref = pick(leads_cols, "ARef")
    L_lender = pick(leads_cols, "LenderId")
    L_date = pick(leads_cols, "DateReceivedUtc", "DateCreatedUtc")
    L_result = pick(leads_cols, "LeadResultTypeId", "LeadResultId")
    L_camp = pick(leads_cols, "CampaignId")
    L_phone = pick(leads_cols, "PhoneNumber", "Phone")
    L_email = pick(leads_cols, "EmailAddress", "Email")
    L_dob = pick(leads_cols, "DateOfBirth")
    L_gov = pick(leads_cols, "GovernmentIdNumber", "NationalIdNumber", "SSN")
    L_nat = pick(leads_cols, "NationalIdNumber")
    L_leadid = pick(leads_cols, "LeadId", "LeadID")

    A_aref = pick(apps_cols, "ARef")
    A_lender = pick(apps_cols, "LenderId")
    A_status = pick(apps_cols, "ApplicationStatusTypeId", "ApplicationStatusId")

    print(
        f"# Leads cols: aref={L_aref} lender={L_lender} date={L_date} "
        f"result={L_result} camp={L_camp} phone={L_phone} email={L_email} "
        f"dob={L_dob} gov={L_gov} nat={L_nat} leadid={L_leadid}",
        flush=True,
    )

    # ─── Brokers.Sources + Campaigns lookups ──────────────────────────
    sources: dict[int, dict] = {}
    campaign_to_source: dict[int, int] = {}

    def load_brokers_from(database: str) -> bool:
        any_loaded = False
        try:
            c2 = pyodbc.connect(conn_str(database), timeout=20)
            c2.timeout = QUERY_TIMEOUT
        except pyodbc.Error as e:
            print(f"# {database} unreachable: {e}", flush=True)
            return False
        try:
            cur2 = c2.cursor()
            scols = discover_columns(cur2, "Sources")
            if scols and not sources:
                sid = pick(scols, "SourceId", "SourceID")
                snm = pick(scols, "FriendlyName", "ShortName", "CompanyName", "Name")
                slender = pick(scols, "LenderId")
                if sid and snm:
                    sel = ", ".join([f"[{sid}]", f"[{snm}]",
                                     f"[{slender}]" if slender else "NULL"])
                    cur2.execute(f"SELECT {sel} FROM dbo.Sources")
                    for i, n, lid in cur2.fetchall():
                        if i is None: continue
                        if lid is not None and slender and int(lid) != LENDER_ID:
                            continue
                        sources[int(i)] = {
                            "source_id":     int(i),
                            "friendly_name": (str(n).strip() if n is not None else "") or f"Source {i}",
                        }
                    print(f"# Sources from {database}: {len(sources)}", flush=True)
                    any_loaded = True
            ccols = discover_columns(cur2, "Campaigns")
            if ccols and not campaign_to_source:
                if "MessageType" not in ccols:
                    cid = pick(ccols, "CampaignId", "CampaignID")
                    csrc = pick(ccols, "SourceId", "SourceID")
                    if cid and csrc:
                        cur2.execute(f"SELECT [{cid}], [{csrc}] FROM dbo.Campaigns")
                        for i, src in cur2.fetchall():
                            if i is None or src is None: continue
                            campaign_to_source[int(i)] = int(src)
                        print(f"# Campaign→Source: {len(campaign_to_source)} mappings from {database}", flush=True)
                        any_loaded = True
        finally:
            c2.close()
        return any_loaded

    for db in ("ReportingBrokers", "ReportingApplications"):
        load_brokers_from(db)
        if sources and campaign_to_source:
            break

    # ─── Part A: weak-accepted source ranking ─────────────────────────
    # Pull per-campaign-id purchased + paid_out counts in window, then roll
    # up to source. Reuses the same CTE pattern as scan_brokers.py but
    # narrower (we only need purchased + paid).
    print("# Part A: per-source purchase + paid_out counts", flush=True)
    cur.execute(
        f"""
        WITH purchased AS (
            SELECT l.[{L_aref}] AS ARef, MAX(l.[{L_camp}]) AS CampaignId
            FROM dbo.Leads l
            WHERE l.[{L_date}] >= ? AND l.[{L_date}] < ?
              AND l.[{L_lender}] = ?
              AND l.[{L_result}] IN ({",".join(str(x) for x in PURCHASED_RESULT_IDS)})
              AND l.[{L_aref}] IS NOT NULL
            GROUP BY l.[{L_aref}]
        ),
        with_status AS (
            SELECT p.CampaignId,
                   p.ARef,
                   MAX(CASE WHEN a.[{A_status}] = 5 THEN 1 ELSE 0 END) AS paid
            FROM purchased p
            INNER JOIN dbo.Applications a ON a.[{A_aref}] = p.ARef AND a.[{A_lender}] = ?
            GROUP BY p.CampaignId, p.ARef
        )
        SELECT CampaignId,
               COUNT(*) AS apps,
               SUM(paid) AS paid_out
        FROM with_status
        GROUP BY CampaignId
        """,
        [window_start, window_end, LENDER_ID, LENDER_ID],
    )
    accepted_per_campaign = {
        (int(cid) if cid is not None else None): (int(apps), int(paid or 0))
        for cid, apps, paid in cur.fetchall()
    }
    print(f"#   campaigns with purchased apps: {len(accepted_per_campaign):,}", flush=True)

    # Per-source rollup
    weak_data: dict[int | None, dict] = {}
    for cid, (apps, paid) in accepted_per_campaign.items():
        sid = campaign_to_source.get(cid) if cid is not None else None
        slot = weak_data.setdefault(sid, {
            "source_id": sid,
            "friendly_name": (sources.get(sid) or {}).get("friendly_name") if sid is not None else "Unknown source",
            "applications": 0,
            "paid_out": 0,
        })
        slot["applications"] += apps
        slot["paid_out"]     += paid

    # We also need leads_purchased per source (some sources have purchased
    # leads that never became apps — those are still relevant). Quick query.
    cur.execute(
        f"""
        SELECT l.[{L_camp}], COUNT(*) AS purchased
        FROM dbo.Leads l
        WHERE l.[{L_date}] >= ? AND l.[{L_date}] < ?
          AND l.[{L_lender}] = ?
          AND l.[{L_result}] IN ({",".join(str(x) for x in PURCHASED_RESULT_IDS)})
        GROUP BY l.[{L_camp}]
        """,
        [window_start, window_end, LENDER_ID],
    )
    for cid, n in cur.fetchall():
        cid_int = int(cid) if cid is not None else None
        sid = campaign_to_source.get(cid_int) if cid_int is not None else None
        slot = weak_data.setdefault(sid, {
            "source_id": sid,
            "friendly_name": (sources.get(sid) or {}).get("friendly_name") if sid is not None else "Unknown source",
            "applications": 0,
            "paid_out": 0,
        })
        slot["leads_purchased"] = slot.get("leads_purchased", 0) + int(n)

    # Compute paid_out_rate per source and stats across the qualifying cohort
    qualifying: list[dict] = []
    for slot in weak_data.values():
        if (slot.get("leads_purchased") or 0) < MIN_VOLUME:
            slot["qualifies"] = False
            continue
        slot["qualifies"] = True
        # Rate = paid out / leads purchased (true end-to-end conversion)
        slot["paid_out_rate"] = (
            slot["paid_out"] / slot["leads_purchased"]
            if slot["leads_purchased"] else 0
        )
        qualifying.append(slot)

    rates = [s["paid_out_rate"] for s in qualifying if s["paid_out_rate"] is not None]
    median_rate = statistics.median(rates) if rates else 0
    q1_rate = (
        statistics.quantiles(rates, n=4)[0] if len(rates) >= 4 else min(rates) if rates else 0
    )
    print(f"# Qualifying sources: {len(qualifying)}  median paid_out_rate: {median_rate:.5f}  Q1: {q1_rate:.5f}", flush=True)

    for s in qualifying:
        s["rate_vs_median"] = (s["paid_out_rate"] / median_rate) if median_rate else None
        # Flag rules: < Q1 = clearly low, < median/2 = severely low, < median = below average
        rate = s["paid_out_rate"]
        if rate < q1_rate:
            s["flag"] = "below Q1"
        elif rate < median_rate:
            s["flag"] = "below median"
        else:
            s["flag"] = None

    qualifying.sort(key=lambda s: s.get("paid_out_rate") or 0)

    # ─── Part B: bounceback analysis of source-excluded leads ─────────
    # First: per-campaign source-excluded counts so we know which sources
    # have meaningful blocked volume.
    print("# Part B: per-source source-excluded counts", flush=True)
    cur.execute(
        f"""
        SELECT l.[{L_camp}], COUNT(*) AS excluded
        FROM dbo.Leads l
        WHERE l.[{L_date}] >= ? AND l.[{L_date}] < ?
          AND l.[{L_lender}] = ?
          AND l.[{L_result}] = ?
        GROUP BY l.[{L_camp}]
        """,
        [window_start, window_end, LENDER_ID, EXCLUDED_RESULT_ID],
    )
    excluded_per_source: dict[int | None, int] = {}
    for cid, n in cur.fetchall():
        cid_int = int(cid) if cid is not None else None
        sid = campaign_to_source.get(cid_int) if cid_int is not None else None
        excluded_per_source[sid] = excluded_per_source.get(sid, 0) + int(n)
    print(f"#   sources with any excluded leads: {len(excluded_per_source):,}", flush=True)
    print(f"#   total excluded leads: {sum(excluded_per_source.values()):,}", flush=True)
    candidate_sources = {sid: n for sid, n in excluded_per_source.items() if n >= MIN_EXCLUDED}
    print(f"#   sources with >= {MIN_EXCLUDED} excluded: {len(candidate_sources):,}", flush=True)

    # Now the heavy join. We do three separate joins (one per identity
    # strategy) and union the results — SQL Server's optimiser handles
    # this far better than a single OR-joined condition.
    # Output: per excluded-SourceId, how many distinct people we later
    # purchased via OTHER sources, and how many of those paid out.
    print("# Part B: running 3-way identity-match join (this is the heavy one)…", flush=True)

    bounceback_per_source: dict[int | None, dict] = {}

    def _ensure_b_slot(sid):
        if sid not in bounceback_per_source:
            bounceback_per_source[sid] = {
                "source_id": sid,
                "friendly_name": (sources.get(sid) or {}).get("friendly_name") if sid is not None else "Unknown source",
                "excluded_count": excluded_per_source.get(sid, 0),
                "match_leadids":  set(),    # excluded LeadIds that matched
                "match_arefs":    set(),    # purchased ARefs that match was found in
                "match_paid_arefs": set(),  # subset of match_arefs that paid out
                "by_strategy":    {"gov_id": 0, "phone_dob": 0, "email_dob": 0},
                "destination_sources": {},  # other source id → bounceback count
            }
        return bounceback_per_source[sid]

    # Each join: pick the rejected leads from sources with ≥MIN_EXCLUDED
    # excluded count (via Campaigns join) and match against PURCHASED leads
    # in the same window via the identity strategy. We exclude same-source
    # matches because a bounceback only counts if it came in via a
    # DIFFERENT source.
    base_join_filter = f"""
            l_e.[{L_date}] >= ? AND l_e.[{L_date}] < ?
            AND l_e.[{L_lender}] = ?
            AND l_e.[{L_result}] = ?
            AND l_p.[{L_date}] >= ? AND l_p.[{L_date}] < ?
            AND l_p.[{L_lender}] = ?
            AND l_p.[{L_result}] IN ({",".join(str(x) for x in PURCHASED_RESULT_IDS)})
            AND l_p.[{L_aref}] IS NOT NULL
    """

    # Strategy 1: GovernmentIdNumber match (SSN)
    if L_gov:
        print(f"#   strategy 1: {L_gov} match…", flush=True)
        sql = f"""
            SELECT c_e.[CampaignId]  AS rej_camp,
                   l_e.[{L_leadid}]  AS rej_lead,
                   l_p.[{L_aref}]    AS pur_aref,
                   c_p.[CampaignId]  AS pur_camp,
                   a.[{A_status}]    AS app_status
            FROM dbo.Leads l_e
            LEFT JOIN dbo.Campaigns c_e ON c_e.[CampaignId] = l_e.[{L_camp}]
            INNER JOIN dbo.Leads l_p
                ON l_p.[{L_gov}] = l_e.[{L_gov}]
            LEFT JOIN dbo.Campaigns c_p ON c_p.[CampaignId] = l_p.[{L_camp}]
            LEFT JOIN dbo.Applications a ON a.[{A_aref}] = l_p.[{L_aref}] AND a.[{A_lender}] = ?
            WHERE {base_join_filter}
              AND l_e.[{L_gov}] IS NOT NULL AND l_e.[{L_gov}] <> ''
        """
        try:
            cur.execute(sql, [
                LENDER_ID,
                window_start, window_end, LENDER_ID, EXCLUDED_RESULT_ID,
                window_start, window_end, LENDER_ID,
            ])
            n = 0
            for rej_camp, rej_lead, pur_aref, pur_camp, app_status in cur.fetchall():
                src_e = campaign_to_source.get(int(rej_camp)) if rej_camp is not None else None
                src_p = campaign_to_source.get(int(pur_camp)) if pur_camp is not None else None
                if src_e == src_p and src_e is not None:
                    continue   # same-source match doesn't count
                slot = _ensure_b_slot(src_e)
                slot["match_leadids"].add(rej_lead)
                slot["match_arefs"].add(pur_aref)
                if app_status is not None and int(app_status) == 5:
                    slot["match_paid_arefs"].add(pur_aref)
                slot["by_strategy"]["gov_id"] += 1
                if src_p is not None:
                    slot["destination_sources"][src_p] = slot["destination_sources"].get(src_p, 0) + 1
                n += 1
            print(f"#     gov_id matches: {n}", flush=True)
        except pyodbc.Error as e:
            print(f"#     gov_id strategy failed: {e}", flush=True)

    # Strategy 2: Phone + DOB
    if L_phone and L_dob:
        print(f"#   strategy 2: {L_phone} + {L_dob} match…", flush=True)
        sql = f"""
            SELECT c_e.[CampaignId]  AS rej_camp,
                   l_e.[{L_leadid}]  AS rej_lead,
                   l_p.[{L_aref}]    AS pur_aref,
                   c_p.[CampaignId]  AS pur_camp,
                   a.[{A_status}]    AS app_status
            FROM dbo.Leads l_e
            LEFT JOIN dbo.Campaigns c_e ON c_e.[CampaignId] = l_e.[{L_camp}]
            INNER JOIN dbo.Leads l_p
                ON l_p.[{L_phone}] = l_e.[{L_phone}]
               AND l_p.[{L_dob}]   = l_e.[{L_dob}]
            LEFT JOIN dbo.Campaigns c_p ON c_p.[CampaignId] = l_p.[{L_camp}]
            LEFT JOIN dbo.Applications a ON a.[{A_aref}] = l_p.[{L_aref}] AND a.[{A_lender}] = ?
            WHERE {base_join_filter}
              AND l_e.[{L_phone}] IS NOT NULL AND l_e.[{L_phone}] <> ''
              AND l_e.[{L_dob}] IS NOT NULL
        """
        try:
            cur.execute(sql, [
                LENDER_ID,
                window_start, window_end, LENDER_ID, EXCLUDED_RESULT_ID,
                window_start, window_end, LENDER_ID,
            ])
            n = 0
            for rej_camp, rej_lead, pur_aref, pur_camp, app_status in cur.fetchall():
                src_e = campaign_to_source.get(int(rej_camp)) if rej_camp is not None else None
                src_p = campaign_to_source.get(int(pur_camp)) if pur_camp is not None else None
                if src_e == src_p and src_e is not None:
                    continue
                slot = _ensure_b_slot(src_e)
                slot["match_leadids"].add(rej_lead)
                slot["match_arefs"].add(pur_aref)
                if app_status is not None and int(app_status) == 5:
                    slot["match_paid_arefs"].add(pur_aref)
                slot["by_strategy"]["phone_dob"] += 1
                if src_p is not None:
                    slot["destination_sources"][src_p] = slot["destination_sources"].get(src_p, 0) + 1
                n += 1
            print(f"#     phone_dob matches: {n}", flush=True)
        except pyodbc.Error as e:
            print(f"#     phone_dob strategy failed: {e}", flush=True)

    # Strategy 3: Email + DOB
    if L_email and L_dob:
        print(f"#   strategy 3: {L_email} + {L_dob} match…", flush=True)
        sql = f"""
            SELECT c_e.[CampaignId]  AS rej_camp,
                   l_e.[{L_leadid}]  AS rej_lead,
                   l_p.[{L_aref}]    AS pur_aref,
                   c_p.[CampaignId]  AS pur_camp,
                   a.[{A_status}]    AS app_status
            FROM dbo.Leads l_e
            LEFT JOIN dbo.Campaigns c_e ON c_e.[CampaignId] = l_e.[{L_camp}]
            INNER JOIN dbo.Leads l_p
                ON l_p.[{L_email}] = l_e.[{L_email}]
               AND l_p.[{L_dob}]   = l_e.[{L_dob}]
            LEFT JOIN dbo.Campaigns c_p ON c_p.[CampaignId] = l_p.[{L_camp}]
            LEFT JOIN dbo.Applications a ON a.[{A_aref}] = l_p.[{L_aref}] AND a.[{A_lender}] = ?
            WHERE {base_join_filter}
              AND l_e.[{L_email}] IS NOT NULL AND l_e.[{L_email}] <> ''
              AND l_e.[{L_dob}] IS NOT NULL
        """
        try:
            cur.execute(sql, [
                LENDER_ID,
                window_start, window_end, LENDER_ID, EXCLUDED_RESULT_ID,
                window_start, window_end, LENDER_ID,
            ])
            n = 0
            for rej_camp, rej_lead, pur_aref, pur_camp, app_status in cur.fetchall():
                src_e = campaign_to_source.get(int(rej_camp)) if rej_camp is not None else None
                src_p = campaign_to_source.get(int(pur_camp)) if pur_camp is not None else None
                if src_e == src_p and src_e is not None:
                    continue
                slot = _ensure_b_slot(src_e)
                slot["match_leadids"].add(rej_lead)
                slot["match_arefs"].add(pur_aref)
                if app_status is not None and int(app_status) == 5:
                    slot["match_paid_arefs"].add(pur_aref)
                slot["by_strategy"]["email_dob"] += 1
                if src_p is not None:
                    slot["destination_sources"][src_p] = slot["destination_sources"].get(src_p, 0) + 1
                n += 1
            print(f"#     email_dob matches: {n}", flush=True)
        except pyodbc.Error as e:
            print(f"#     email_dob strategy failed: {e}", flush=True)

    conn.close()

    # ─── Finalise Part B output ───────────────────────────────────────
    blocked_rows = []
    for sid, slot in bounceback_per_source.items():
        excluded = slot["excluded_count"]
        if excluded < MIN_EXCLUDED:
            continue
        bounce_n = len(slot["match_leadids"])
        bounce_ar = len(slot["match_arefs"])
        paid_n = len(slot["match_paid_arefs"])
        # Top 5 destination sources by where the excluded people went
        dest_rows = sorted(slot["destination_sources"].items(), key=lambda kv: -kv[1])[:5]
        top_destinations = [
            {
                "source_id": s,
                "friendly_name": (sources.get(s) or {}).get("friendly_name") if s is not None else f"Source {s}",
                "bounced_count": n,
            }
            for s, n in dest_rows
        ]
        blocked_rows.append({
            "source_id":            slot["source_id"],
            "friendly_name":        slot["friendly_name"],
            "excluded_count":       excluded,
            "bounceback_leads":     bounce_n,
            "bounceback_arefs":     bounce_ar,
            "bounceback_paid":      paid_n,
            "bounceback_rate":      (bounce_n / excluded) if excluded else None,
            "bounceback_paid_rate": (paid_n / bounce_ar) if bounce_ar else None,
            "bounceback_paid_per_excluded": (paid_n / excluded) if excluded else None,
            "by_strategy":          slot["by_strategy"],
            "top_destinations":     top_destinations,
        })

    # Sort by paid-per-excluded descending — sources where blocking is costing us
    # the most paid loans rise to the top.
    blocked_rows.sort(key=lambda r: -(r.get("bounceback_paid_per_excluded") or 0))

    # ─── Finalise Part A output ───────────────────────────────────────
    # Drop rows where weak_data is missing leads_purchased (means they had
    # apps without a Lead row, edge case).
    weak_rows = sorted(
        [s for s in qualifying if s.get("leads_purchased")],
        key=lambda s: s.get("paid_out_rate") or 0,
    )

    output = {
        "snapshot_at":   started.isoformat(),
        "snapshot_date": started.date().isoformat(),
        "lender_id":     LENDER_ID,
        "lender_label":  LENDER_LABEL,
        "window_days":   WINDOW_DAYS,
        "window_start":  window_start.date().isoformat(),
        "window_end":    window_end.date().isoformat(),
        "min_volume_for_ranking":   MIN_VOLUME,
        "min_excluded_for_ranking": MIN_EXCLUDED,
        "weak_accepted": {
            "median_paid_out_rate":  median_rate,
            "q1_paid_out_rate":      q1_rate,
            "qualifying_sources":    len(qualifying),
            "sources":               weak_rows,
        },
        "blocked_to_reconsider":    blocked_rows,
    }
    out_path = Path("source-quality.json")
    out_path.write_text(json.dumps(output, indent=2, default=str))
    print(
        f"# wrote {out_path} ({out_path.stat().st_size:,} bytes); "
        f"{len(weak_rows)} ranked accepted sources; "
        f"{len(blocked_rows)} blocked sources with bounceback data",
        flush=True,
    )


if __name__ == "__main__":
    main()
