#!/usr/bin/env python3
"""
build_admins.py — regenerate admins.json from people.json.

admins.json drives the Cloudflare Worker's admin-gate (fetchAdmins).
The Worker auto-syncs it on every people-set that touches access_level
/ suspended / main_google_email / alt_google_emails, but if nobody
edits an admin's record for a while the file can go stale. This script
is the catch-up: re-derive the full list from people.json and write it.

Logic:
  - Owner (james.benamor@letme.com) always included as failsafe.
  - Every Person with access_level == "admin" and !suspended → include
    main_google_email + all alt_google_emails + external_google_email.

Outputs sorted, deduplicated. Re-runnable.

USAGE
  python3 scripts/build_admins.py            # dry-run
  python3 scripts/build_admins.py --apply
  python3 scripts/build_admins.py --apply --commit
"""
from __future__ import annotations
import argparse, datetime as dt, json, pathlib, subprocess

REPO   = pathlib.Path(__file__).resolve().parent.parent
PEOPLE = REPO / "people.json"
OUT    = REPO / "admins.json"
OWNER  = "james.benamor@letme.com"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply",  action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    if args.commit: args.apply = True

    ppl = json.loads(PEOPLE.read_text())["people"]
    emails = set([OWNER.lower()])
    admin_persons = 0
    for p in ppl:
        if p.get("access_level") != "admin": continue
        if p.get("suspended"): continue
        admin_persons += 1
        if p.get("main_google_email"): emails.add(p["main_google_email"].lower())
        for e in (p.get("alt_google_emails") or []):
            if e: emails.add(e.lower())
        if p.get("external_google_email"): emails.add(p["external_google_email"].lower())

    new = {
        "schema_version": 1,
        "updated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "generated from people.json (access_level=admin, not suspended)",
        "admins": sorted(emails),
    }
    print(f"admin Persons: {admin_persons}  →  {len(emails)} unique email(s)")
    for e in sorted(emails): print(f"  {e}")

    # Detect whether the existing file already matches — if so, no-op
    # (lets the workflow exit cleanly without an empty commit).
    if OUT.exists():
        try:
            cur = json.loads(OUT.read_text())
            if cur.get("admins") == new["admins"]:
                print("\nadmins.json already in sync — nothing to do.")
                return
        except Exception:
            pass

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to write.\n")
        return

    OUT.write_text(json.dumps(new, indent=2) + "\n")
    print(f"\n✓ Wrote {OUT.relative_to(REPO)}")

    if args.commit:
        msg = f"Admins: sync from people.json ({len(emails)} email(s))"
        subprocess.run(["git", "add", "admins.json"], cwd=REPO, check=True)
        subprocess.run(["git", "commit", "-m", msg], cwd=REPO, check=True)
        subprocess.run(["git", "pull", "--rebase", "--quiet"], cwd=REPO, check=True)
        subprocess.run(["git", "push"], cwd=REPO, check=True)
        print("✓ Committed + pushed.\n")


if __name__ == "__main__":
    main()
