"""
Build per-endpoint sample customer interaction histories for the Pipeline page.

For each "dead end" on the application-progression Sankey (the red drop nodes
where a customer's journey with us ended), pick 25 random ARefs that ended
there and pull their full interaction timeline from the warehouse:

  - Application creation event
  - Tasks completed (Apply1, BRW signed, GT signed, GT credit check, GT VC, …)
  - ESignatures (sign events)
  - WebBehaviours (web visits)
  - Communications.Messages (inbound + outbound)

Robot-typed messages get their bodies redacted to "<date, time, Message from
MessageBot>". Inbound from customer + outbound from a human agent (CRM) keep
their full body text.

Endpoints (strict mutual exclusion — each customer = furthest stage reached):
  - abandoned_before_page1 — Application started, no Task 41 GtRef=null done
  - dropped_before_brw_signed — Apply1 done, no Task 48 GtRef=null done
  - no_accepted_guarantor — BRW signed, no Task 54 GtRef!=null done
  - no_vc_reached — GT credit check done, no Task 62/146 GtRef!=null done
  - vc_ready_not_paid_out — GT VC done, ApplicationStatusTypeId != 5

Output: `pipeline-samples.json` at repo root.

Required env vars (same set as scan_pipeline.py):
  FABRIC_SQL_ENDPOINT, FABRIC_TENANT_ID, FABRIC_CLIENT_ID, FABRIC_CLIENT_SECRET
"""
from __future__ import annotations

import datetime
import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

import pyodbc

LENDER_ID = 6
LENDER_LABEL = "Transform Credit (LenderId 6, USA)"
WINDOW_YEAR = 2026
WINDOW_MONTH = 3
SAMPLE_SIZE = 25
RNG_SEED = 20260510      # deterministic so re-runs produce the same sample

QUERY_TIMEOUT = 600

# ClientTypes that are robots/automated systems — message bodies get redacted
# to a one-liner. Everything else (TogetherLoansCRM = human agent in CRM,
# TogetherLoansWebsite = the customer themselves, etc.) keeps its body.
ROBOT_CLIENT_TYPES = {
    "MessageFactory",
    "AutoReconcileProcessor",
    "RobotResponders",
    "MessageReplyBot",
    "AutoCollectCards",
    "MFSenderRobot",
    "PaymentsFactory",
    "CardDeactivator",
    "DailyUpdate",
    "MiniUpdate",
    "MonitorRobot",
    "WhiteboxRun",
    "TogetherLoansWhitebox",
    "SensitiveDataDeleter",
    "EmailInWebjob",
    "TranscriptionRobot",
}

# TaskTypeID labels for the timeline (from the wiki).
TASK_TYPE_LABELS = {
    41:  "BRW Details (Apply1)",
    48:  "Sign contract",
    49:  "Bank linked",
    54:  "Credit check",
    55:  "Columbo",
    57:  "Card linked",
    62:  "Verbal contract",
    96:  "Budget plan",
    146: "Verbal contract (medical)",
    150: "Verbal contract (top-up)",
    173: "Verbal contract (medallion bank)",
}


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


def chunked(seq, n):
    """Yield successive n-sized chunks from seq."""
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def main() -> None:
    started = datetime.datetime.now(datetime.timezone.utc)
    month_start = datetime.date(WINDOW_YEAR, WINDOW_MONTH, 1)
    if WINDOW_MONTH == 12:
        month_end = datetime.date(WINDOW_YEAR + 1, 1, 1)
    else:
        month_end = datetime.date(WINDOW_YEAR, WINDOW_MONTH + 1, 1)
    print(f"# scan_pipeline_samples start {started.isoformat()}  window: {month_start} → {month_end}", flush=True)

    rng = random.Random(RNG_SEED)

    # ─────────────────────────────────────────────────────────────────
    # Phase 1 — pull every March-cohort ARef + the stages each one reached.
    #          This drives the bucket assignment.
    # ─────────────────────────────────────────────────────────────────
    apps_conn = pyodbc.connect(conn_str("ReportingApplications"), timeout=20)
    apps_conn.timeout = QUERY_TIMEOUT
    cur = apps_conn.cursor()

    # Discover columns
    apps_cols = discover_columns(cur, "Applications")
    tasks_cols = discover_columns(cur, "Tasks")

    apps_aref = pick(apps_cols, "ARef")
    apps_lender = pick(apps_cols, "LenderId")
    apps_date = pick(apps_cols, "InterestingDateTimeUtc", "DateCreatedUtc", "InterestingDateTimeUTC")
    apps_status = pick(apps_cols, "ApplicationStatusTypeId")
    apps_leadid = pick(apps_cols, "LeadId", "LeadID")
    tasks_aref = pick(tasks_cols, "ARef", "Aref")
    tasks_type = pick(tasks_cols, "TaskTypeId", "TaskTypeID")
    tasks_done = pick(tasks_cols, "DateCompletedUtc", "DateCompletedUTC")
    tasks_gtref = pick(tasks_cols, "GtRef", "GTRef")

    print(f"# Applications: {apps_aref}/{apps_lender}/{apps_date}/{apps_status}/{apps_leadid}", flush=True)
    print(f"# Tasks: {tasks_aref}/{tasks_type}/{tasks_done}/{tasks_gtref}", flush=True)

    # All March-cohort ARefs + their current ApplicationStatus
    print("# Q1: pull all March-cohort ARefs + ApplicationStatusTypeId", flush=True)
    cur.execute(
        f"""
        SELECT [{apps_aref}], [{apps_status}], [{apps_date}], [{apps_leadid}]
        FROM dbo.Applications
        WHERE [{apps_date}] >= ? AND [{apps_date}] < ?
          AND [{apps_lender}] = ?
          AND [{apps_aref}] IS NOT NULL
        """,
        [month_start, month_end, LENDER_ID],
    )
    aref_to_app = {}
    for arow in cur.fetchall():
        aref, status, dt, leadid = arow
        aref_to_app[aref] = {
            "status_id": int(status) if status is not None else None,
            "created": dt,
            "lead_id": leadid,
        }
    print(f"#   cohort size: {len(aref_to_app):,}", flush=True)

    # Stage reach per ARef from Tasks
    print("# Q2: pull task-completion reach per ARef", flush=True)
    cur.execute(
        f"""
        SELECT t.[{tasks_aref}], t.[{tasks_type}],
               CASE WHEN t.[{tasks_gtref}] IS NULL THEN 'BRW' ELSE 'GT' END AS who
        FROM dbo.Tasks t
        WHERE t.[{tasks_aref}] IN (
            SELECT [{apps_aref}]
            FROM dbo.Applications
            WHERE [{apps_date}] >= ? AND [{apps_date}] < ?
              AND [{apps_lender}] = ?
              AND [{apps_aref}] IS NOT NULL
        )
          AND t.[{tasks_done}] IS NOT NULL
          AND t.[{tasks_type}] IN (41, 48, 54, 62, 146)
        """,
        [month_start, month_end, LENDER_ID],
    )
    aref_stages: dict[str, set] = defaultdict(set)
    for r in cur.fetchall():
        aref, ttid, who = r[0], int(r[1]), r[2]
        aref_stages[aref].add((ttid, who))
    print(f"#   ARefs with ≥1 stage event: {len(aref_stages):,}", flush=True)

    apps_conn.close()

    # ─────────────────────────────────────────────────────────────────
    # Bucket each ARef into its furthest stage's "ended here" endpoint.
    # ─────────────────────────────────────────────────────────────────
    def furthest_endpoint(aref: str) -> str:
        s = aref_stages.get(aref, set())
        info = aref_to_app[aref]
        has_apply1   = (41, 'BRW') in s
        has_brw_sign = (48, 'BRW') in s
        has_gt_pass  = (54, 'GT')  in s
        has_gt_vc    = (62, 'GT')  in s or (146, 'GT') in s
        is_paid_out  = info['status_id'] == 5
        # Strict furthest stage (mutual exclusion)
        if is_paid_out:                   return "paid_out"
        if has_gt_vc:                     return "vc_ready_not_paid_out"
        if has_gt_pass:                   return "no_vc_reached"
        if has_brw_sign:                  return "no_accepted_guarantor"
        if has_apply1:                    return "dropped_before_brw_signed"
        return "abandoned_before_page1"

    by_endpoint: dict[str, list[str]] = defaultdict(list)
    for aref in aref_to_app:
        by_endpoint[furthest_endpoint(aref)].append(aref)

    print(f"# bucket sizes: { {k: len(v) for k, v in by_endpoint.items()} }", flush=True)

    # ─────────────────────────────────────────────────────────────────
    # Sample SAMPLE_SIZE ARefs per dead-end endpoint (skip paid_out).
    # ─────────────────────────────────────────────────────────────────
    DEAD_ENDS = [
        "abandoned_before_page1",
        "dropped_before_brw_signed",
        "no_accepted_guarantor",
        "no_vc_reached",
        "vc_ready_not_paid_out",
    ]
    samples: dict[str, list[str]] = {}
    all_sampled: list[str] = []
    for ep in DEAD_ENDS:
        pool = by_endpoint.get(ep, [])
        n = min(SAMPLE_SIZE, len(pool))
        samples[ep] = rng.sample(pool, n) if n > 0 else []
        all_sampled.extend(samples[ep])
        print(f"#   {ep}: pool={len(pool):,}  sampled={n}", flush=True)

    if not all_sampled:
        print("# no samples; writing empty file", flush=True)
        Path("pipeline-samples.json").write_text(json.dumps({"endpoints": {}}, indent=2))
        return

    # ─────────────────────────────────────────────────────────────────
    # Phase 2 — pull interaction events for the sampled ARefs.
    #          Re-open the Apps connection (we closed it above).
    # ─────────────────────────────────────────────────────────────────
    apps_conn = pyodbc.connect(conn_str("ReportingApplications"), timeout=20)
    apps_conn.timeout = QUERY_TIMEOUT
    cur = apps_conn.cursor()

    interactions: dict[str, list[dict]] = defaultdict(list)

    # 1. Application creation event (one per ARef)
    for aref in all_sampled:
        info = aref_to_app[aref]
        if info['created']:
            interactions[aref].append({
                "kind": "application_started",
                "at": info['created'].isoformat() if hasattr(info['created'], 'isoformat') else str(info['created']),
                "label": "Application started" + (f" (from purchased lead #{info['lead_id']})" if info['lead_id'] is not None else " (direct via website)"),
            })

    # 2. Tasks
    print("# pulling Tasks for sampled ARefs…", flush=True)
    for chunk in chunked(all_sampled, 1500):
        ph = ",".join(["?"] * len(chunk))
        cur.execute(
            f"""
            SELECT [{tasks_aref}], [{tasks_type}], [{tasks_gtref}],
                   [{tasks_done}], Description
            FROM dbo.Tasks
            WHERE [{tasks_aref}] IN ({ph})
              AND [{tasks_done}] IS NOT NULL
            """,
            chunk,
        )
        for aref, ttid, gtref, done, descr in cur.fetchall():
            label = TASK_TYPE_LABELS.get(int(ttid), f"Task #{ttid}")
            who = "GT" if gtref is not None else "BRW"
            interactions[aref].append({
                "kind": "task_completed",
                "at": done.isoformat() if hasattr(done, 'isoformat') else str(done),
                "label": f"{who} completed: {label}",
                "task_type_id": int(ttid),
                "description": (descr or "").strip() if descr else None,
            })

    # 3. ESignatures
    es_cols = discover_columns(cur, "ESignatures")
    es_aref = pick(es_cols, "ARef", "Aref")
    es_signed = pick(es_cols, "DateSignedUtc", "DateSignedUTC", "DateSignedLocal")
    es_doc = pick(es_cols, "DocumentType", "Type", "ContractType", "DocumentName")
    es_gtref = pick(es_cols, "GtRef", "GTRef")
    print(f"# ESignatures cols: aref={es_aref} signed={es_signed} doc={es_doc} gtref={es_gtref}", flush=True)
    if es_aref and es_signed:
        for chunk in chunked(all_sampled, 1500):
            ph = ",".join(["?"] * len(chunk))
            doc_sql = f", [{es_doc}]" if es_doc else ", NULL"
            gtref_sql = f", [{es_gtref}]" if es_gtref else ", NULL"
            cur.execute(
                f"""
                SELECT [{es_aref}], [{es_signed}]{doc_sql}{gtref_sql}
                FROM dbo.ESignatures
                WHERE [{es_aref}] IN ({ph})
                  AND [{es_signed}] IS NOT NULL
                """,
                chunk,
            )
            for aref, signed, doc, gtref in cur.fetchall():
                who = "GT" if gtref is not None else "BRW"
                interactions[aref].append({
                    "kind": "signature",
                    "at": signed.isoformat() if hasattr(signed, 'isoformat') else str(signed),
                    "label": f"{who} signed" + (f": {doc}" if doc else ""),
                })

    # 4. WebBehaviours
    wb_cols = discover_columns(cur, "WebBehaviours")
    wb_aref = pick(wb_cols, "ARef", "Aref")
    wb_dt = pick(wb_cols, "DateTimeUtc", "DateTimeUTC", "DateCreatedUtc")
    wb_url = pick(wb_cols, "Url", "Page", "PageUrl", "Path")
    wb_action = pick(wb_cols, "Action", "EventType", "Behaviour")
    print(f"# WebBehaviours cols: aref={wb_aref} dt={wb_dt} url={wb_url} action={wb_action}", flush=True)
    if wb_aref and wb_dt:
        for chunk in chunked(all_sampled, 1500):
            ph = ",".join(["?"] * len(chunk))
            url_sql = f", [{wb_url}]" if wb_url else ", NULL"
            act_sql = f", [{wb_action}]" if wb_action else ", NULL"
            cur.execute(
                f"""
                SELECT [{wb_aref}], [{wb_dt}]{url_sql}{act_sql}
                FROM dbo.WebBehaviours
                WHERE [{wb_aref}] IN ({ph})
                  AND [{wb_dt}] IS NOT NULL
                """,
                chunk,
            )
            for aref, dt, url, act in cur.fetchall():
                bits = []
                if act: bits.append(str(act))
                if url: bits.append(str(url))
                interactions[aref].append({
                    "kind": "web_visit",
                    "at": dt.isoformat() if hasattr(dt, 'isoformat') else str(dt),
                    "label": "Web: " + " · ".join(bits) if bits else "Web visit",
                })

    apps_conn.close()

    # 5. Messages — different DB
    print("# pulling Messages from ReportingCommunications…", flush=True)
    comm_conn = pyodbc.connect(conn_str("ReportingCommunications"), timeout=20)
    comm_conn.timeout = QUERY_TIMEOUT
    cur = comm_conn.cursor()
    msg_cols = discover_columns(cur, "Messages")
    print(f"# Messages cols: {sorted(msg_cols)}", flush=True)
    msg_aref = pick(msg_cols, "ARef", "Aref")
    msg_dt = pick(msg_cols, "DateTimeUtc", "DateTimeUTC", "DateCreatedUtc", "DateSentUtc")
    msg_ctype = pick(msg_cols, "ClientType")
    msg_cuser = pick(msg_cols, "ClientUsername", "ClientUserName")
    msg_descr = pick(msg_cols, "Description")
    msg_body = pick(msg_cols, "MessageBody", "Body", "Content", "Message")
    msg_subject = pick(msg_cols, "Subject")
    msg_external = pick(msg_cols, "ExternalAddress")
    print(f"# Messages chosen: aref={msg_aref} dt={msg_dt} ct={msg_ctype} body={msg_body}", flush=True)
    if msg_aref and msg_dt:
        for chunk in chunked(all_sampled, 1500):
            ph = ",".join(["?"] * len(chunk))
            body_sql = f", [{msg_body}]" if msg_body else ", NULL"
            descr_sql = f", [{msg_descr}]" if msg_descr else ", NULL"
            ctype_sql = f", [{msg_ctype}]" if msg_ctype else ", NULL"
            subj_sql = f", [{msg_subject}]" if msg_subject else ", NULL"
            cur.execute(
                f"""
                SELECT [{msg_aref}], [{msg_dt}]{body_sql}{descr_sql}{ctype_sql}{subj_sql}
                FROM dbo.Messages
                WHERE [{msg_aref}] IN ({ph})
                  AND [{msg_dt}] IS NOT NULL
                """,
                chunk,
            )
            for aref, dt, body, descr, ctype, subj in cur.fetchall():
                ctype_str = (ctype or "").strip()
                descr_int = int(descr) if descr is not None and str(descr).strip() != "" else None
                # Inbound from customer = Description IN (0,1,2)
                is_inbound = descr_int in (0, 1, 2)
                # Robot if ClientType is in our known robot set, OR Description suggests a robot
                # outbound type. We err on showing-body if uncertain.
                is_robot = (not is_inbound) and (ctype_str in ROBOT_CLIENT_TYPES)
                channel = {0: "SMS in", 1: "Email in", 2: "Call in"}.get(descr_int, None)
                if not channel:
                    channel = "Outbound" + (f" ({ctype_str})" if ctype_str else "")
                msg = {
                    "kind": "message_in" if is_inbound else "message_out",
                    "at": dt.isoformat() if hasattr(dt, 'isoformat') else str(dt),
                    "channel": channel,
                    "client_type": ctype_str or None,
                }
                if is_robot:
                    msg["label"] = f"Message from {ctype_str}Bot"
                    msg["redacted"] = True
                else:
                    body_text = (body or "").strip() if body else ""
                    if subj:
                        body_text = f"[{subj}] {body_text}".strip()
                    if body_text:
                        # Cap message body length so the JSON doesn't explode on
                        # 50KB email threads.
                        if len(body_text) > 4000:
                            body_text = body_text[:4000] + " …[truncated]"
                        msg["body"] = body_text
                    else:
                        msg["body"] = "(empty body)"
                interactions[aref].append(msg)
    comm_conn.close()

    # ─────────────────────────────────────────────────────────────────
    # Sort each ARef's interactions chronologically and assemble output.
    # ─────────────────────────────────────────────────────────────────
    for aref, evs in interactions.items():
        evs.sort(key=lambda e: e["at"])

    out_endpoints = {}
    for ep, arefs in samples.items():
        out_endpoints[ep] = [
            {
                "aref": aref,
                "interaction_count": len(interactions.get(aref, [])),
                "interactions": interactions.get(aref, []),
            }
            for aref in arefs
        ]

    output = {
        "snapshot_at": started.isoformat(),
        "snapshot_date": started.date().isoformat(),
        "lender_id": LENDER_ID,
        "lender_label": LENDER_LABEL,
        "month": f"{WINDOW_YEAR:04d}-{WINDOW_MONTH:02d}",
        "month_label": month_start.strftime("%B %Y"),
        "sample_size_per_endpoint": SAMPLE_SIZE,
        "endpoints": out_endpoints,
        "endpoint_labels": {
            "abandoned_before_page1":     "Abandoned before page 1",
            "dropped_before_brw_signed":  "Dropped before BRW signed",
            "no_accepted_guarantor":      "No accepted guarantor",
            "no_vc_reached":              "No VC reached",
            "vc_ready_not_paid_out":      "VC ready but not paid out",
        },
    }
    out_path = Path("pipeline-samples.json")
    out_path.write_text(json.dumps(output, indent=2, default=str))
    total_events = sum(len(c["interactions"]) for ep_list in out_endpoints.values() for c in ep_list)
    print(f"# wrote {out_path} ({out_path.stat().st_size:,} bytes); total events {total_events:,}", flush=True)


if __name__ == "__main__":
    main()
