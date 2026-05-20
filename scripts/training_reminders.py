#!/usr/bin/env python3
"""training_reminders.py — daily reminder + auto-enrol sweep for the
harassment-prevention training module.

Designed to run from a GitHub Action. Has two modes:

  --auto-enrol            sweep people.json for new-hires + line managers
                          and assign them the relevant modules

  --reminders             send today's reminder emails (10/5/2/0 days +
                          day-15 escalation to line manager + HR)

  --dry-run               combine with either mode to print what would
                          be done without writing/sending

State lives in the repo:
  training-assignments.json   who owes what, with deadlines
  training-events.json        append-only audit (reminder-sent events
                              are written here so we don't double-send)
  training-config.json        cycle config + signing officer

Email transport: SMTP (re-uses the existing SMTP_USERNAME / SMTP_PASSWORD
secrets already wired in .github/workflows/email-payroll-monthly.yml).
"""

from __future__ import annotations
import argparse
import base64
import datetime as dt
import json
import os
import smtplib
import sys
import time
from email.mime.text import MIMEText
from typing import Any

import requests

REPO    = os.environ.get("GITHUB_REPOSITORY", "richmondbot2000-prog/togetherbook")
BRANCH  = os.environ.get("GITHUB_REF_NAME", "main")
TOKEN   = os.environ.get("GITHUB_TOKEN") or os.environ.get("TRAINING_GH_TOKEN")
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
HR_CC = [a.strip() for a in (os.environ.get("HR_ESCALATION_CC", "")).split(",") if a.strip()]

GH_API = "https://api.github.com"
SESSION = requests.Session()
SESSION.headers.update({
    "Accept": "application/vnd.github+json",
    "User-Agent": "togetherbook-training-reminders",
})
if TOKEN:
    SESSION.headers["Authorization"] = f"Bearer {TOKEN}"


# ── REPO IO ──────────────────────────────────────────────────────────

def gh_get_file(path: str) -> tuple[dict, str | None]:
    """Read a JSON file from the repo. Returns (parsed_json, sha)."""
    r = SESSION.get(f"{GH_API}/repos/{REPO}/contents/{path}?ref={BRANCH}")
    if r.status_code == 404:
        return ({}, None)
    r.raise_for_status()
    data = r.json()
    raw = base64.b64decode(data["content"])
    return (json.loads(raw.decode("utf-8")), data["sha"])


def gh_put_file(path: str, content: dict, sha: str | None, message: str) -> None:
    """Write a JSON file back to the repo."""
    encoded = base64.b64encode(
        (json.dumps(content, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    ).decode("ascii")
    body: dict[str, Any] = {"message": message, "content": encoded, "branch": BRANCH}
    if sha:
        body["sha"] = sha
    r = SESSION.put(f"{GH_API}/repos/{REPO}/contents/{path}", data=json.dumps(body))
    if not r.ok:
        raise RuntimeError(f"PUT {path} → {r.status_code}: {r.text[:300]}")


def append_event(events_doc: dict, event: dict) -> None:
    events_doc.setdefault("schema_version", 1)
    events_doc.setdefault("events", []).append(event)
    events_doc["updated_at"] = event.get("ts") or now_iso()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_iso() -> str:
    return dt.datetime.utcnow().date().isoformat()


# ── EMAIL ────────────────────────────────────────────────────────────

REMINDER_TEMPLATES = {
    10: ("[TogetherBook training] {cycle} cycle — 10 days to go",
         "Hi {first},\n\nThe harassment-prevention training cycle is due on {deadline}. "
         "You have 10 days, which is plenty — most modules take 10–12 minutes.\n\n"
         "Open the dashboard: https://book.togetherbook.net/training.html\n\n"
         "Thanks,\nTogetherBOOK"),
    5: ("[TogetherBook training] {cycle} cycle — 5 days to go",
        "Hi {first},\n\nFive days to go on the harassment-prevention cycle. "
        "If you can find 30 minutes this week the whole thing is done.\n\n"
        "Open the dashboard: https://book.togetherbook.net/training.html\n\n"
        "Thanks,\nTogetherBOOK"),
    2: ("[TogetherBook training] {cycle} cycle — 2 days to go",
        "Hi {first},\n\nThe harassment-prevention training is due on {deadline} — "
        "two days away. Please pick up where you left off when you have 30 minutes.\n\n"
        "Open the dashboard: https://book.togetherbook.net/training.html\n\n"
        "Thanks,\nTogetherBOOK"),
    0: ("[TogetherBook training] {cycle} cycle — overdue",
        "Hi {first},\n\nThe deadline for the harassment-prevention training was {deadline}. "
        "Please complete the remaining modules by {deadline_plus_7}. "
        "After that date your line manager and HR are notified automatically.\n\n"
        "Open the dashboard: https://book.togetherbook.net/training.html\n\n"
        "Thanks,\nTogetherBOOK"),
}
ESCALATION_TEMPLATE = (
    "[TogetherBook training] {name} — overdue",
    "Hi {manager_first},\n\n{name}'s harassment-prevention training was due on "
    "{deadline} and is now overdue. HR has also been copied.\n\n"
    "A short note from you asking how you can help find the time often unblocks this.\n\n"
    "The dashboard: https://book.togetherbook.net/training.html\n\n"
    "Thanks,\nTogetherBOOK\n",
)


def send_email(to: str, cc: list[str], subject: str, body: str, dry_run: bool) -> dict:
    if dry_run or not SMTP_USERNAME or not SMTP_PASSWORD:
        return {
            "ok": True, "dry_run": True,
            "to": to, "cc": cc, "subject": subject,
            "body_first_line": body.split("\n", 1)[0],
        }
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = f"TogetherBOOK Training <{SMTP_USERNAME}>"
    msg["To"] = to
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(SMTP_USERNAME, SMTP_PASSWORD)
        s.sendmail(SMTP_USERNAME, [to] + cc, msg.as_string())
    return {"ok": True, "dry_run": False, "to": to, "cc": cc, "subject": subject}


# ── REMINDER LOGIC ───────────────────────────────────────────────────

def resolve_person(people: list[dict], email: str) -> tuple[dict | None, str, dict | None]:
    e = (email or "").lower()
    person = None
    for p in people:
        emails = [p.get("main_google_email") or ""] + (p.get("alt_google_emails") or []) + [p.get("external_google_email") or ""]
        if any((x or "").lower() == e for x in emails):
            person = p
            break
    first = e.split("@")[0]
    manager = None
    if person:
        first = person.get("given") or (person.get("name") or "").split(" ")[0] or first
        lm_id = person.get("line_manager_id")
        if lm_id is not None and lm_id != "":
            manager = next((p for p in people if str(p.get("id")) == str(lm_id)), None)
    return (person, first, manager)


def run_reminders(dry_run: bool) -> dict:
    assignments_doc, _    = gh_get_file("training-assignments.json")
    events_doc,  events_sha = gh_get_file("training-events.json")
    config_doc,  _          = gh_get_file("training-config.json")
    people_doc,  _          = gh_get_file("people.json")
    assignments = assignments_doc.get("assignments", []) if assignments_doc else []
    events      = events_doc.get("events", []) if events_doc else []
    people      = people_doc.get("people", []) if people_doc else []
    cycle_year  = (config_doc or {}).get("current_cycle_year") or dt.date.today().year
    offsets     = (config_doc or {}).get("reminder_offsets_days") or [10, 5, 2, 0]
    escalate_at = (config_doc or {}).get("escalation_overdue_days") or 15

    today = dt.date.today()
    today_str = today.isoformat()

    # Dedupe set: events already sent today, keyed by (kind, email, module-group-key).
    sent_today = set()
    for ev in events:
        if ev.get("type") != "reminder_sent":
            continue
        ts = ev.get("ts") or ""
        if not ts.startswith(today_str):
            continue
        sent_today.add((ev.get("kind", ""), (ev.get("user_email") or "").lower(), ev.get("module_id", "")))

    # Already-completed modules — skip reminders for them.
    completed = {(ev["user_email"].lower(), ev["module_id"]) for ev in events
                 if ev.get("type") == "module_completed" and ev.get("user_email") and ev.get("module_id")}

    by_user_kind: dict[tuple[str, str], list[dict]] = {}
    for a in assignments:
        if a.get("exempt"):
            continue
        email = (a.get("user_email") or "").lower()
        module = a.get("module_id") or ""
        if (email, module) in completed:
            continue
        deadline = a.get("deadline") or ""
        if not deadline:
            continue
        try:
            due_date = dt.date.fromisoformat(deadline)
        except ValueError:
            continue
        days_left = (due_date - today).days
        overdue   = -days_left
        kind = None
        if days_left in offsets and days_left > 0:
            kind = str(days_left)
        elif days_left == 0:
            kind = "0"
        elif overdue == escalate_at:
            kind = "esc"
        if not kind:
            continue
        by_user_kind.setdefault((email, kind), []).append(a)

    results = {"dry_run": dry_run, "sent": 0, "skipped_already_sent": 0,
               "items": [], "today": today_str}

    new_events: list[dict] = []
    for (email, kind), items in sorted(by_user_kind.items()):
        modules_key = ",".join(sorted(a["module_id"] for a in items))
        if (kind, email, modules_key) in sent_today:
            results["skipped_already_sent"] += 1
            continue
        person, first, manager = resolve_person(people, email)
        earliest = min(a["deadline"] for a in items)
        try:
            earliest_dt = dt.date.fromisoformat(earliest)
        except ValueError:
            earliest_dt = today
        deadline_plus_7 = (earliest_dt + dt.timedelta(days=7)).isoformat()

        if kind == "esc":
            if not manager:
                results["items"].append({"email": email, "kind": kind, "skip": "no line manager set"})
                continue
            m_email = (manager.get("main_google_email") or "").lower()
            m_first = manager.get("given") or (manager.get("name") or "").split(" ")[0] or "there"
            subj_t, body_t = ESCALATION_TEMPLATE
            subject = subj_t.format(name=(person.get("name") if person else email))
            body    = body_t.format(manager_first=m_first,
                                    name=(person.get("name") if person else email),
                                    deadline=earliest)
            r = send_email(m_email, HR_CC, subject, body, dry_run)
            results["items"].append({**r, "kind": kind, "for": email})
            if r.get("ok") and not r.get("dry_run"):
                results["sent"] += 1
            new_events.append({
                "type": "reminder_sent",
                "user_email": email, "manager_email": m_email,
                "module_id": modules_key, "kind": "esc",
                "dry_run": bool(r.get("dry_run")),
                "ts": now_iso(),
            })
            continue

        offset_int = int(kind) if kind != "0" else 0
        subj_t, body_t = REMINDER_TEMPLATES[offset_int]
        subject = subj_t.format(cycle=cycle_year)
        body    = body_t.format(first=first, deadline=earliest, deadline_plus_7=deadline_plus_7, cycle=cycle_year)
        r = send_email(email, [], subject, body, dry_run)
        results["items"].append({**r, "kind": kind, "modules": [a["module_id"] for a in items]})
        if r.get("ok") and not r.get("dry_run"):
            results["sent"] += 1
        new_events.append({
            "type": "reminder_sent", "user_email": email,
            "module_id": modules_key, "kind": kind,
            "dry_run": bool(r.get("dry_run")),
            "ts": now_iso(),
        })

    if new_events and not dry_run and TOKEN:
        # Re-fetch in case of races, then append.
        events_doc, events_sha = gh_get_file("training-events.json")
        for ev in new_events:
            append_event(events_doc, ev)
        gh_put_file("training-events.json", events_doc, events_sha,
                    f"Training reminders: {len(new_events)} event{'' if len(new_events) == 1 else 's'} on {today_str}")
    results["new_events"] = len(new_events)
    return results


# ── AUTO-ENROL ───────────────────────────────────────────────────────

def run_auto_enrol(dry_run: bool) -> dict:
    config_doc,  _ = gh_get_file("training-config.json")
    assignments_doc, ass_sha = gh_get_file("training-assignments.json")
    people_doc, _  = gh_get_file("people.json")
    config = config_doc or {}
    assignments = assignments_doc.get("assignments", []) if assignments_doc else []
    people = people_doc.get("people", []) if people_doc else []

    all_staff_modules  = config.get("modules_all_staff") or ["module_0","module_1","module_2","module_3","module_4","module_5"]
    manager_modules    = config.get("modules_manager_addon") or ["module_manager"]
    new_hire_days      = config.get("deadline_days_new_hire") or 30
    manager_days       = config.get("deadline_days_manager_addon") or 14

    today = dt.date.today()
    new_starter_window = today - dt.timedelta(days=14)

    # Build manager-id set.
    manager_ids = set()
    for p in people:
        lm = p.get("line_manager_id")
        if lm is not None and lm != "":
            manager_ids.add(str(lm))

    # Lookup of existing assignments to avoid duplicates.
    existing = {((a.get("user_email") or "").lower(), a.get("module_id")) for a in assignments}

    new_entries = []
    new_hires = 0
    managers = 0
    for p in people:
        e = (p.get("main_google_email") or "").lower()
        if not e or p.get("suspended"):
            continue
        start = p.get("start_date") or ""
        try:
            start_dt = dt.date.fromisoformat(start) if start else None
        except ValueError:
            start_dt = None
        is_new = bool(start_dt and start_dt >= new_starter_window)
        is_mgr = str(p.get("id")) in manager_ids
        if is_new:
            for m in all_staff_modules:
                if (e, m) in existing:
                    continue
                new_entries.append({"user_email": e, "module_id": m,
                                    "assigned_at": now_iso(),
                                    "deadline": (today + dt.timedelta(days=new_hire_days)).isoformat(),
                                    "reason": "new_hire", "exempt": False})
                existing.add((e, m))
            new_hires += 1
        if is_mgr:
            for m in manager_modules:
                if (e, m) in existing:
                    continue
                new_entries.append({"user_email": e, "module_id": m,
                                    "assigned_at": now_iso(),
                                    "deadline": (today + dt.timedelta(days=manager_days)).isoformat(),
                                    "reason": "manager_appointment", "exempt": False})
                existing.add((e, m))
            if not is_new:
                managers += 1

    result = {"dry_run": dry_run, "new_hires": new_hires, "managers": managers, "new_assignments": len(new_entries)}
    if new_entries and not dry_run and TOKEN:
        # Re-fetch + write.
        assignments_doc, ass_sha = gh_get_file("training-assignments.json")
        assignments_doc.setdefault("schema_version", 1)
        assignments_doc.setdefault("assignments", []).extend(new_entries)
        assignments_doc["updated_at"] = now_iso()
        gh_put_file("training-assignments.json", assignments_doc, ass_sha,
                    f"Training: auto-enrol sweep — {len(new_entries)} new")
    return result


# ── ENTRY POINT ──────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--auto-enrol", action="store_true")
    p.add_argument("--reminders", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if not args.auto_enrol and not args.reminders:
        print("nothing to do — pass --auto-enrol and/or --reminders", file=sys.stderr)
        return 2
    if args.auto_enrol:
        out = run_auto_enrol(args.dry_run)
        print("auto-enrol:", json.dumps(out, indent=2))
    if args.reminders:
        out = run_reminders(args.dry_run)
        print("reminders:", json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
