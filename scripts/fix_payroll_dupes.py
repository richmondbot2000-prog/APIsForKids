#!/usr/bin/env python3
"""
fix_payroll_dupes.py — clean up auto-created Persons from the payroll
import that are actually the same human as an existing Google-account
Person. Merges them and copies payroll-side fields back onto the
surviving Person where empty.

Re-runnable: skips entries that have already been merged.

USAGE
  python3 scripts/fix_payroll_dupes.py            # dry-run
  python3 scripts/fix_payroll_dupes.py --apply
  python3 scripts/fix_payroll_dupes.py --apply --commit
"""
from __future__ import annotations
import argparse, datetime as dt, json, pathlib, subprocess

REPO    = pathlib.Path(__file__).resolve().parent.parent
PEOPLE  = REPO / "people.json"
PAYROLL = REPO / "payroll-data.json"

# (loser_url_slug, winner_url_slug). Loser absorbed into winner.
MERGES = [
    ("rachid.james.benamor",  "james.benamor"),
    ("benjamin.gardner",      "ben.gardner"),
    ("daniel.meineck",        "dan.meineck"),
    ("matthew.brunet",        "matt.brunet"),
    ("maximillian.dynowski",  "max.dynowski"),
    ("saoirse.polywka",       "saoirse-brooke.polywka"),
    ("stanislav.majerski",    "stan.majerski"),
    ("yik.chan",              "yikyu.chan"),
    ("ashwin.alummoottil",    "ashwin.john"),
]


def find_by_slug(people, slug):
    for p in people:
        if (p.get("url_slug") or "").lower() == slug.lower(): return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply",  action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    if args.commit: args.apply = True

    pf = json.loads(PEOPLE.read_text())
    payf = json.loads(PAYROLL.read_text())
    people, records = pf["people"], payf["records"]
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    merged = []
    enriched = []

    # ── 1. Run the explicit merges ────────────────────────────────────
    for loser_slug, winner_slug in MERGES:
        loser  = find_by_slug(people, loser_slug)
        winner = find_by_slug(people, winner_slug)
        if not loser:
            print(f"  skip merge {loser_slug} → {winner_slug}  (loser already gone)")
            continue
        if not winner:
            print(f"  ! winner {winner_slug} not found for merge of {loser_slug}")
            continue

        # Copy fields onto winner where empty.
        for k in ("phone", "address", "start_date"):
            if not (winner.get(k) or "").strip() and (loser.get(k) or "").strip():
                winner[k] = loser[k]
        # Aliases: loser's name + given/family combos.
        aliases = set(winner.get("aliases") or [])
        if loser.get("name") and loser["name"] != winner.get("name"): aliases.add(loser["name"])
        winner["aliases"] = sorted(aliases)

        # on_payroll + payroll link.
        if loser.get("on_payroll"): winner["on_payroll"] = True
        if loser.get("most_recent_payroll_id") and not winner.get("most_recent_payroll_id"):
            winner["most_recent_payroll_id"] = loser["most_recent_payroll_id"]

        # Re-point every PayrollData row from loser → winner.
        repointed = 0
        for r in records:
            if r.get("person_id") == loser["id"]:
                r["person_id"] = winner["id"]
                repointed += 1

        # Delete loser.
        people.remove(loser)
        winner["updated_at"] = now
        print(f"  ✓ merge: {loser['name']!r} (id={loser['id']}) → {winner['name']!r} (id={winner['id']}) — {repointed} payroll row(s) re-pointed")
        merged.append((loser["name"], winner["name"]))

    # ── 2. Sweep: for every Person on payroll, copy fields from the
    # active payroll record onto the Person where empty. ──────────────
    by_id = {r["id"]: r for r in records}
    for p in people:
        rec = by_id.get(p.get("most_recent_payroll_id"))
        if not rec: continue
        changes = []
        for src_k, dst_k in [("mobile", "phone"), ("address", "address"), ("start_date", "start_date")]:
            src_v = (rec.get(src_k) or "").strip()
            if not src_v: continue
            if not (p.get(dst_k) or "").strip():
                p[dst_k] = src_v
                changes.append(dst_k)
        if changes:
            p["updated_at"] = now
            enriched.append((p["name"], changes))

    print(f"\nmerges done: {len(merged)}")
    print(f"persons enriched from payroll: {len(enriched)}")
    for name, fields in enriched[:20]:
        print(f"  {name:<30} ← {', '.join(fields)}")
    if len(enriched) > 20:
        print(f"  ... +{len(enriched)-20} more")

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to write.\n")
        return

    pf["updated_at"] = now
    payf["updated_at"] = now
    PEOPLE.write_text(json.dumps(pf, indent=2, ensure_ascii=False) + "\n")
    PAYROLL.write_text(json.dumps(payf, indent=2, ensure_ascii=False) + "\n")
    print("\n✓ Wrote both files.")

    # Also re-build google-accounts.json + admins.json since we removed Persons.
    subprocess.run(["python3", "scripts/build_google_accounts.py", "--apply"], cwd=REPO, check=True, capture_output=True)
    subprocess.run(["python3", "scripts/build_admins.py", "--apply"], cwd=REPO, check=True, capture_output=True)
    print("✓ Rebuilt google-accounts.json + admins.json")

    if args.commit:
        msg = (f"Payroll dupes: merge {len(merged)} auto-created Persons + "
               f"copy {len(enriched)} field(s) from payroll → Person\n\n"
               + "\n".join(f"- {l} → {w}" for l, w in merged))
        subprocess.run(["git", "add", "people.json", "payroll-data.json",
                        "google-accounts.json", "admins.json"],
                       cwd=REPO, check=True)
        subprocess.run(["git", "commit", "-m", msg], cwd=REPO, check=True)
        subprocess.run(["git", "pull", "--rebase", "--quiet"], cwd=REPO, check=True)
        subprocess.run(["git", "push"], cwd=REPO, check=True)
        print("✓ Committed + pushed.\n")


if __name__ == "__main__":
    main()
