"""
Per-user, per-15-min-bucket activity scanner.

Rebuilt 2026-05-18: previously this script auto-discovered every warehouse
table with a ClientUsername column and counted any row as "the human was
active at that bucket". That caught a lot of bot writes credited to humans
(messaging factories, robot responders, scheduler IDs reusing an agent's
username, etc.) — visible symptom was people lit up 24/7 in the Holidays
Activity bar.

The replacement is intentionally narrow: read `scripts/activity_sources.json`
(the canonical whitelist) and ONLY scan those sources, applying each
source's explicit `human_filter` verbatim. If the Activity bar looks wrong,
the rule belongs in `activity_sources.json` — not buried in here.

Output is unchanged so the front-end / D1 mirror keep working:
  - `staff-activity-buckets.json` at the repo root
  - same shape (schema_version: 2, by_email: {email: {buckets, events}})
  - same merge-window semantics
  - same D1 sync into `activity_buckets` + `activity_events`

Date-range envvars (optional):
  ACTIVITY_START_DATE  YYYY-MM-DD  — first day to scan (inclusive)
  ACTIVITY_END_DATE    YYYY-MM-DD  — last day to scan (inclusive)
Default: both = yesterday UTC.

Required env vars: FABRIC_SQL_ENDPOINT, FABRIC_TENANT_ID, FABRIC_CLIENT_ID, FABRIC_CLIENT_SECRET
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pyodbc


SOURCES_FILE = Path(__file__).parent / "activity_sources.json"
DEFAULT_LOOKBACK_DAYS = 1
QUERY_TIMEOUT = 240


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


def load_sources():
    if not SOURCES_FILE.exists():
        sys.exit(f"error: {SOURCES_FILE} missing — the activity scanner needs an explicit whitelist")
    cfg = json.loads(SOURCES_FILE.read_text())
    srcs = cfg.get("sources") or []
    if not srcs:
        sys.exit("error: activity_sources.json has no `sources` entries — nothing to scan")
    for s in srcs:
        for key in ("database", "schema", "table", "ts_col", "user_col", "human_filter", "label"):
            if not s.get(key):
                sys.exit(f"error: activity_sources.json entry missing `{key}`: {s}")
    return srcs


def scan_source(src, start: datetime.datetime, end_exclusive: datetime.datetime, buckets_out, events_out):
    """Run the source's whitelisted query and aggregate into the shared dicts.
    Per-source key (used as `src` in the events doc) is `<db-short>.<table>`
    where db-short = database minus 'Reporting' prefix, lower-cased — matches
    the existing shape so the front-end keeps rendering."""
    database = src["database"]
    schema   = src["schema"]
    table    = src["table"]
    ts       = src["ts_col"]
    user_col = src["user_col"]
    where    = src["human_filter"]
    label    = src["label"]
    db_short = database.removeprefix("Reporting").lower()
    src_key  = f"{db_short}.{table}"

    print(f"# {label} — {database}.{schema}.{table}  (filter: {where})", flush=True)

    try:
        c = pyodbc.connect(conn_str(database), timeout=20)
        c.timeout = QUERY_TIMEOUT
        cur = c.cursor()
    except Exception as e:
        print(f"  ! connect failed: {e}", flush=True)
        return

    start_str = start.strftime("%Y-%m-%d %H:%M:%S")
    end_str   = end_exclusive.strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Same person-shape gate as before: ClientUsername must look like an
        # email (contains @) or dotted local-part (contains .). Both forms
        # appear in CRM logs depending on whether the agent was signed in
        # via SSO email or bare username.
        q = (
            f"SELECT LOWER([{user_col}]) AS un, "
            f"       CAST([{ts}] AS DATE) AS dt, "
            f"       (DATEPART(HOUR, [{ts}]) * 4 + DATEPART(MINUTE, [{ts}]) / 15) AS bucket, "
            f"       COUNT_BIG(*) AS writes, "
            f"       MIN([{ts}]) AS first_at, "
            f"       MAX([{ts}]) AS last_at "
            f"FROM [{schema}].[{table}] "
            f"WHERE [{ts}] >= ? AND [{ts}] < ? "
            f"  AND [{user_col}] IS NOT NULL "
            f"  AND ([{user_col}] LIKE '%@%' OR [{user_col}] LIKE '%.%') "
            f"  AND ({where}) "
            f"GROUP BY LOWER([{user_col}]), CAST([{ts}] AS DATE), "
            f"         (DATEPART(HOUR, [{ts}]) * 4 + DATEPART(MINUTE, [{ts}]) / 15)"
        )
        cur.execute(q, [start_str, end_str])
        rows_seen = 0
        for un, dt, bucket, writes, first_at, last_at in cur.fetchall():
            iso = dt.isoformat() if dt else None
            if not iso or bucket is None:
                continue
            buckets_out[un][iso].add(int(bucket))
            key = (un, iso, src_key, int(bucket))
            ev = events_out.get(key)
            if ev is None:
                events_out[key] = {
                    "src":      src_key,
                    "label":    label,
                    "bucket":   int(bucket),
                    "writes":   int(writes or 0),
                    "first_at": first_at.isoformat() if first_at else None,
                    "last_at":  last_at.isoformat()  if last_at  else None,
                }
            else:
                ev["writes"] += int(writes or 0)
                if first_at and (not ev["first_at"] or first_at.isoformat() < ev["first_at"]): ev["first_at"] = first_at.isoformat()
                if last_at  and (not ev["last_at"]  or last_at.isoformat()  > ev["last_at"]):  ev["last_at"]  = last_at.isoformat()
            rows_seen += 1
        print(f"  · {rows_seen:,} (user, day, bucket) groups returned", flush=True)
    except Exception as e:
        print(f"  ! {schema}.{table}: {e}", flush=True)
    finally:
        try: c.close()
        except: pass


def domain_local_variants(workspace_email: str):
    """Every ClientUsername form this Workspace user might appear under.
    Unchanged from the old scanner — CRM stores agent identifiers as either
    a full SSO email, a tenant-local email, or a bare local-part."""
    local = workspace_email.split("@")[0].lower()
    domains = [
        "rgroup.co.uk", "letme.co.uk", "letme.com",
        "transformcredit.com", "togetherloans.com",
        "lendingmate.ca", "rapida.bg", "rapidamoney.pl",
        "clearloans.com.au", "fianceo.com",
        "tandolan.dk", "tandolaina.fi",
    ]
    s = {f"{local}@{d}" for d in domains}
    s.add(workspace_email.lower())
    s.add(local)
    return s


def parse_date(s: str | None):
    if not s:
        return None
    try:
        return datetime.datetime.strptime(s.strip(), "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
    except Exception:
        sys.exit(f"error: bad date '{s}' — expected YYYY-MM-DD")


def main() -> None:
    started = datetime.datetime.now(datetime.timezone.utc)
    today = started.date()
    yesterday = today - datetime.timedelta(days=1)

    start = parse_date(os.environ.get("ACTIVITY_START_DATE")) or datetime.datetime(
        yesterday.year, yesterday.month, yesterday.day, tzinfo=datetime.timezone.utc)
    end_inclusive = parse_date(os.environ.get("ACTIVITY_END_DATE")) or datetime.datetime(
        yesterday.year, yesterday.month, yesterday.day, tzinfo=datetime.timezone.utc)
    end_exclusive = end_inclusive + datetime.timedelta(days=1)

    sources = load_sources()
    print(f"# scan_staff_activity_buckets start {started.isoformat()}", flush=True)
    print(f"# range:   {start.date().isoformat()} → {end_inclusive.date().isoformat()} (inclusive)", flush=True)
    print(f"# sources: {len(sources)} whitelisted (see scripts/activity_sources.json)", flush=True)

    dates_in_window = []
    d = start.date()
    while d <= end_inclusive.date():
        dates_in_window.append(d.isoformat())
        d = d + datetime.timedelta(days=1)
    window_set = set(dates_in_window)

    all_buckets = defaultdict(lambda: defaultdict(set))
    all_events  = {}
    for src in sources:
        scan_source(src, start, end_exclusive, all_buckets, all_events)

    staff_path = Path("staff.json")
    if not staff_path.exists():
        sys.exit("staff.json missing — cannot map ClientUsernames to staff")
    staff = json.loads(staff_path.read_text())
    rolled_buckets = defaultdict(lambda: defaultdict(set))
    rolled_events  = defaultdict(lambda: defaultdict(list))
    for u in staff.get("users", []):
        email = (u.get("email") or "").lower()
        if not email:
            continue
        variants = domain_local_variants(email)
        for un in variants:
            if un in all_buckets:
                for iso, buckets in all_buckets[un].items():
                    rolled_buckets[email][iso] |= buckets
        for (un, iso, src_key, bucket), row in all_events.items():
            if un in variants:
                rolled_events[email][iso].append(row)

    out_path = Path("staff-activity-buckets.json").resolve()
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
        except Exception:
            existing = {}
    else:
        existing = {}
    by_email = existing.get("by_email") or {}

    for email, rec in by_email.items():
        for iso in dates_in_window:
            if rec.get("buckets") and iso in rec["buckets"]: del rec["buckets"][iso]
            if rec.get("events")  and iso in rec["events"]:  del rec["events"][iso]

    for email, dates in rolled_buckets.items():
        rec = by_email.setdefault(email, {"buckets": {}, "events": {}})
        rec.setdefault("buckets", {})
        rec.setdefault("events", {})
        for iso, buckets in dates.items():
            if iso not in window_set: continue
            rec["buckets"][iso] = sorted(buckets)
    for email, dates in rolled_events.items():
        rec = by_email.setdefault(email, {"buckets": {}, "events": {}})
        rec.setdefault("events", {})
        for iso, evs in dates.items():
            if iso not in window_set: continue
            evs.sort(key=lambda e: e.get("first_at") or "")
            rec["events"][iso] = evs[:200]

    existing["schema_version"] = 2
    existing["last_pull_at"]   = started.isoformat()
    existing["by_email"]       = by_email
    existing["active_count"]   = len(by_email)
    existing["sources"]        = [
        {"label": s["label"], "src": f"{s['database'].removeprefix('Reporting').lower()}.{s['table']}",
         "filter": s["human_filter"], "description": s.get("description", "")}
        for s in sources
    ]
    pulled = existing.setdefault("pulled", {})
    for iso in dates_in_window:
        pulled[iso] = started.isoformat()

    out_path.write_text(json.dumps(existing, indent=2))
    print(f"# wrote {out_path} — merged {len(rolled_buckets)} users across {len(dates_in_window)} day(s)", flush=True)

    cf_account = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    cf_token   = os.environ.get("CLOUDFLARE_API_TOKEN")
    cf_db      = os.environ.get("D1_ACTIVITY_DB_ID")
    if cf_account and cf_token and cf_db:
        sync_to_d1(cf_account, cf_token, cf_db, rolled_buckets, rolled_events, dates_in_window)
    else:
        print("# CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID / D1_ACTIVITY_DB_ID not set — skipping D1 sync", flush=True)


def _d1_query(account, token, db_id, sql, params=None):
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/d1/database/{db_id}/query"
    body = json.dumps({"sql": sql, "params": params or []}).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def sync_to_d1(account, token, db_id, rolled_buckets, rolled_events, dates_in_window):
    """Idempotent DELETE-then-INSERT of the window into D1's activity_buckets +
    activity_events."""
    print(f"# D1 sync: {len(dates_in_window)} day(s) × buckets={sum(len(v) for v in rolled_buckets.values())} events={sum(len(d) for v in rolled_events.values() for d in v.values())}", flush=True)
    t0 = time.time()

    for iso in dates_in_window:
        for tbl in ("activity_buckets", "activity_events"):
            out = _d1_query(account, token, db_id,
                            f"DELETE FROM {tbl} WHERE iso_date = ?", [iso])
            if not out.get("success"):
                print(f"  ! delete {tbl} {iso} failed: {out.get('errors')}", flush=True)
                return

    bucket_rows = []
    for email, dates in rolled_buckets.items():
        for iso, bset in dates.items():
            if iso not in set(dates_in_window):
                continue
            for b in bset:
                bucket_rows.append((email, iso, int(b)))
    event_rows = []
    for email, dates in rolled_events.items():
        for iso, evs in dates.items():
            if iso not in set(dates_in_window):
                continue
            for ev in evs:
                event_rows.append((
                    email, iso, int(ev["bucket"]), ev["src"],
                    int(ev.get("writes") or 0),
                    ev.get("first_at"), ev.get("last_at"),
                    ev.get("kind") or "warehouse",
                ))

    def _batch_insert(table, cols, rows, batch_n):
        if not rows:
            return
        sql_head = f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES "
        batches = [rows[i:i+batch_n] for i in range(0, len(rows), batch_n)]
        print(f"  · {table}: {len(rows):,} rows in {len(batches):,} batches × {batch_n}", flush=True)
        ok = 0; failed = []
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {}
            for chunk in batches:
                ph = ",".join(["(" + ",".join(["?"]*len(cols)) + ")"] * len(chunk))
                params = [v for row in chunk for v in row]
                futs[ex.submit(_d1_query, account, token, db_id, sql_head + ph, params)] = len(chunk)
            for f in as_completed(futs):
                n = futs[f]
                out = f.result()
                if not out.get("success"):
                    failed.append(out.get("errors"))
                else:
                    ok += n
        if failed:
            print(f"    ! {len(failed)} batch(es) failed; first error: {json.dumps(failed[0])[:300]}", flush=True)
        print(f"    {ok:,}/{len(rows):,} rows inserted into {table}", flush=True)

    _batch_insert("activity_buckets", ["email","iso_date","bucket"], bucket_rows, 33)
    _batch_insert("activity_events",  ["email","iso_date","bucket","src","writes","first_at","last_at","kind"], event_rows, 12)
    print(f"# D1 sync done in {time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
