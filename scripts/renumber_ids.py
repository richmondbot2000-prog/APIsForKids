#!/usr/bin/env python3
"""
renumber_ids.py — one-shot migration. Replaces slug-style ids with
incremental integers across people.json + payroll-data.json, while
preserving the slug as a separate `url_slug` field (used in URLs only).

Run ONCE, after which all writes go through the worker which auto-
assigns integer ids on create.

After this runs:
  people.json:
    - id: integer (1..N, assigned in current sort order)
    - url_slug: string (was the old id; used in /directory/<slug>)
    - line_manager_id: integer (or null)
    - most_recent_payroll_id: integer (or null)
  payroll-data.json:
    - id: integer (1..M)
    - person_id: integer (FK -> people.id)

USAGE
    python3 scripts/renumber_ids.py            # dry-run, prints diff stats
    python3 scripts/renumber_ids.py --apply    # write the new files
    python3 scripts/renumber_ids.py --apply --commit
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys

REPO    = pathlib.Path(__file__).resolve().parent.parent
PEOPLE  = REPO / "people.json"
PAYROLL = REPO / "payroll-data.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply",  action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    if args.commit: args.apply = True

    pf = json.loads(PEOPLE.read_text())
    payf = json.loads(PAYROLL.read_text())
    people  = pf.get("people", [])
    records = payf.get("records", [])

    # Already migrated? Detect by looking at first person id.
    if people and isinstance(people[0].get("id"), int):
        print("people.json already migrated (id is integer). Nothing to do.")
        return

    # Stable sort: by current id slug so the migration is deterministic.
    people.sort(key=lambda p: (p.get("id") or "").lower())
    records.sort(key=lambda r: r.get("imported_at", ""))

    # ── People: assign new integer ids ────────────────────────────────
    person_slug_to_id = {}
    for i, p in enumerate(people, start=1):
        old_slug = p.get("id")
        if not old_slug:
            print(f"!! person at index {i-1} has no old id, skipping renumber", file=sys.stderr)
            continue
        person_slug_to_id[old_slug] = i
        p["id"]       = i
        p["url_slug"] = old_slug

    # Re-point line_manager_id (string slug -> integer).
    relinked_mgr = 0
    for p in people:
        old_mgr = p.get("line_manager_id") or ""
        if isinstance(old_mgr, str) and old_mgr in person_slug_to_id:
            p["line_manager_id"] = person_slug_to_id[old_mgr]
            relinked_mgr += 1
        elif old_mgr == "" or old_mgr is None:
            p["line_manager_id"] = None
        # If it's a string we can't resolve, blank it.
        elif isinstance(old_mgr, str):
            p["line_manager_id"] = None

    # ── PayrollData: assign new integer ids + relink person_id ────────
    payroll_old_to_new = {}
    for i, r in enumerate(records, start=1):
        payroll_old_to_new[r.get("id")] = i
        r["id"] = i
        old_pid = r.get("person_id")
        if isinstance(old_pid, str) and old_pid in person_slug_to_id:
            r["person_id"] = person_slug_to_id[old_pid]
        elif old_pid in (None, ""):
            r["person_id"] = None
        # else: leave as-is — orphan / unmatched

    # Re-point Person.most_recent_payroll_id (string pay_xxx -> integer).
    relinked_pay = 0
    for p in people:
        old = p.get("most_recent_payroll_id") or ""
        if isinstance(old, str) and old in payroll_old_to_new:
            p["most_recent_payroll_id"] = payroll_old_to_new[old]
            relinked_pay += 1
        elif old in (None, ""):
            p["most_recent_payroll_id"] = None
        elif isinstance(old, str):
            p["most_recent_payroll_id"] = None

    # ── Stats + write ─────────────────────────────────────────────────
    print(f"people:  {len(people)} renumbered  ({relinked_mgr} line_manager_id relinks)")
    print(f"payroll: {len(records)} renumbered ({relinked_pay} most_recent_payroll_id relinks)")

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to write.\n")
        return

    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pf["people"]      = people
    pf["updated_at"]  = now
    payf["records"]   = records
    payf["updated_at"] = now

    # Keep people sorted by name for readable diffs going forward.
    pf["people"].sort(key=lambda p: (p.get("name") or "").lower())

    PEOPLE.write_text(json.dumps(pf, indent=2, ensure_ascii=False) + "\n")
    PAYROLL.write_text(json.dumps(payf, indent=2, ensure_ascii=False) + "\n")
    print("\n✓ Wrote both files.")

    if args.commit:
        msg = ("Migration: integer PKs for People + PayrollData\n\n"
               "- people.id and payroll-data.id are now integers (1..N)\n"
               "- people.url_slug carries the old slug for /directory/<slug>\n"
               "- All foreign keys (line_manager_id, most_recent_payroll_id,\n"
               "  person_id) re-pointed to integers\n"
               "- Migration run via scripts/renumber_ids.py (one-shot)\n")
        subprocess.run(["git", "add", "people.json", "payroll-data.json"], cwd=REPO, check=True)
        subprocess.run(["git", "commit", "-m", msg], cwd=REPO, check=True)
        subprocess.run(["git", "pull", "--rebase", "--quiet"], cwd=REPO, check=True)
        subprocess.run(["git", "push"], cwd=REPO, check=True)
        print("✓ Committed + pushed.\n")


if __name__ == "__main__":
    main()
