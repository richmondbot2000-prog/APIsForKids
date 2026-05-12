#!/usr/bin/env python3
"""Process the two payroll CSVs in ~/Desktop/wiki/Payroll into a single JSON
keyed by email (where available) and by normalised name (otherwise).

The output is intended to be pasted as the PAYROLL_JSON secret on the
apifk-workspace-worker Cloudflare Worker. The Worker serves it via
GET /api/workspace/payroll behind Cloudflare Access — i.e. neither the repo
nor the github.io public URL ever sees the personal data.

Usage:
    # write to a local file (gitignored)
    python3 scripts/scan_payroll.py --out /tmp/payroll.json

    # pipe straight to clipboard for pasting into the Worker secret
    python3 scripts/scan_payroll.py | pbcopy
"""
import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

PAYROLL_DIR = Path("~/Desktop/wiki/Payroll").expanduser()
LETME_FILE = (
    "LetMe_Property_Management_Limited_-_Employee_Contact_Details.xlsx"
    " - Employee Contact Details.csv"
)
TLRG_FILE = "For James EmployeeDetails-20260512 (1).xlsx - Export.csv"


def norm_name(first, last):
    return f"{(first or '').strip().lower()} {(last or '').strip().lower()}".strip()


def parse_date(s):
    """Accept a variety of formats — UK staff CSV uses '20 Nov 1988', TL/RG
    export uses '4/6/1990' which is US-style M/D/Y. Tries each candidate."""
    if not s or not s.strip():
        return None
    s = s.strip()
    for fmt in ("%d %b %Y", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return s  # fall back to the raw string


def calc_age(dob_iso):
    if not dob_iso or len(dob_iso) != 10:
        return None
    try:
        dob = datetime.strptime(dob_iso, "%Y-%m-%d").date()
        today = datetime.today().date()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except ValueError:
        return None


def load_letme():
    """LetMe Property CSV: has email + single-field address."""
    rows = []
    with (PAYROLL_DIR / LETME_FILE).open(newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            # Skip the 4 title rows + the header row. Data rows start with a
            # numeric Employee Number.
            if not row or not row[0].strip().isdigit():
                continue
            cells = (row + [""] * 10)[:10]
            emp_no, first, last, dob, age, address, email, start, end, group = cells
            dob_iso = parse_date(dob)
            rows.append({
                "employer": "LetMe Property Management",
                "employee_number": emp_no.strip(),
                "first_name": first.strip(),
                "last_name": last.strip(),
                "email": (email or "").strip().lower() or None,
                "dob": dob_iso,
                "age": calc_age(dob_iso) if dob_iso else (int(age) if age.strip().isdigit() else None),
                "mobile": None,
                "address": address.strip() or None,
                "start_date": parse_date(start),
                "termination_date": parse_date(end),
                "employee_group": group.strip() or None,
            })
    return rows


def load_tlrg():
    """TL/R Group CSV: no email, multi-line address, has mobile."""
    rows = []
    with (PAYROLL_DIR / TLRG_FILE).open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            first = (row.get("First name") or "").strip()
            last = (row.get("Surname") or "").strip()
            if not first and not last:
                continue
            dob_iso = parse_date(row.get("Date of birth"))
            address_lines = [
                row.get("Postal address line 1"),
                row.get("Postal address line 2"),
                row.get("Postal City"),
                row.get("Postal County"),
                row.get("Postal postcode"),
            ]
            address = ", ".join(p.strip() for p in address_lines if p and p.strip())
            rows.append({
                "employer": "Together Loans / R Group",
                "employee_number": (row.get("External Id") or "").strip() or None,
                "first_name": first,
                "last_name": last,
                "email": None,
                "dob": dob_iso,
                "age": calc_age(dob_iso),
                "mobile": (row.get("Mobile") or "").strip() or None,
                "address": address or None,
                "start_date": parse_date(row.get("Start date")),
                "termination_date": None,
                "employee_group": None,
            })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write to file (otherwise stdout)")
    args = ap.parse_args()

    all_rows = load_letme() + load_tlrg()
    by_email = {}
    by_name = {}
    for r in all_rows:
        if r["email"]:
            by_email[r["email"]] = r
        if r["first_name"] and r["last_name"]:
            by_name[norm_name(r["first_name"], r["last_name"])] = r

    output = {
        "schema_version": 1,
        "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": {
            "total": len(all_rows),
            "letme": sum(1 for r in all_rows if r["employer"].startswith("LetMe")),
            "tl_rg": sum(1 for r in all_rows if r["employer"].startswith("Together")),
            "with_email": len(by_email),
        },
        "by_email": by_email,
        "by_name": by_name,
    }

    js = json.dumps(output, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(js, encoding="utf-8")
        print(f"Wrote {len(all_rows)} payroll records to {args.out}", file=sys.stderr)
    else:
        print(js)


if __name__ == "__main__":
    main()
