"""
Daily cron: finalise any pending convert-to-group operations whose 20-day
Google email-reuse lockout has expired.

How it works:
- The Directory page records each conversion as an annotation:
    annotations[<original_email>] = {
        ...other-fields,
        "pending_conversion": {
            "forward_to": "...",
            "scheduled_for": "<ISO>",   # nominally deleted_at + 20 days
            "parked_at": "...",
            "deleted_at": "<ISO>"
        }
    }
- This script reads annotations.json, for each pending_conversion whose
  scheduled_for is in the past it tries to:
    1. Create a Group at the original email address (with the target as member)
    2. On success: remove the pending_conversion field from the annotation,
       commit the updated annotations.json back to the repo.
    3. On failure (still locked, or other error): leave it for the next day's run.

Auth: same WORKSPACE_SERVICE_ACCOUNT_JSON + WORKSPACE_DELEGATE_USER as the
other workflows. Same DWD scopes already authorised.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.group",
    "https://www.googleapis.com/auth/admin.directory.group.member",
]
ANNOTATIONS_PATH = Path("annotations.json")


def env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"error: {name} not set")
    return v


def build_service():
    key_info = json.loads(env("WORKSPACE_SERVICE_ACCOUNT_JSON"))
    delegate = env("WORKSPACE_DELEGATE_USER")
    creds = service_account.Credentials.from_service_account_info(
        key_info, scopes=SCOPES, subject=delegate)
    return build("admin", "directory_v1", credentials=creds, cache_discovery=False)


def main() -> None:
    if not ANNOTATIONS_PATH.exists():
        print("no annotations.json — nothing to do")
        return
    data = json.loads(ANNOTATIONS_PATH.read_text(encoding="utf-8"))
    annotations = data.get("annotations") or {}
    now = datetime.datetime.utcnow()

    pending = []
    for key, ann in annotations.items():
        if not isinstance(ann, dict):
            continue
        pc = ann.get("pending_conversion")
        if not pc:
            continue
        try:
            sched = datetime.datetime.fromisoformat(pc["scheduled_for"].replace("Z", ""))
        except Exception:
            print(f"  skip {key}: malformed scheduled_for {pc.get('scheduled_for')!r}")
            continue
        pending.append((key, ann, pc, sched))

    if not pending:
        print("no pending conversions")
        return

    print(f"{len(pending)} pending conversion(s); {sum(1 for _, _, _, s in pending if s <= now)} ready to finalise")
    if not any(s <= now for _, _, _, s in pending):
        return

    svc = build_service()
    changed = False
    for key, ann, pc, sched in pending:
        if sched > now:
            days_left = (sched - now).days
            print(f"  {key}: not yet ({days_left} day(s) left)")
            continue
        forward_to = pc.get("forward_to")
        if not forward_to:
            print(f"  {key}: no forward_to — skipping")
            continue
        try:
            print(f"  {key}: creating group + adding {forward_to}…")
            svc.groups().insert(body={
                "email": key,
                "name": (key.split("@")[0].replace(".", " ").replace("_", " ").replace("-", " ") + " (ex-employee)"),
                "description": (
                    f"Forwarding-only group at {key}. Created on "
                    f"{now.strftime('%Y-%m-%d')} after the Workspace user was offboarded "
                    f"(scheduled via convert-to-group on {pc.get('deleted_at', '?')})."
                ),
            }).execute()
            svc.members().insert(groupKey=key, body={
                "email": forward_to,
                "role": "MEMBER",
            }).execute()
            print(f"  {key}: OK")
            ann.pop("pending_conversion", None)
            if not ann:
                annotations.pop(key, None)
            changed = True
        except HttpError as e:
            print(f"  {key}: failed ({e.resp.status}) — leaving for next run; details: {e.error_details or e.reason or e}")
            continue

    if changed:
        data["annotations"] = annotations
        data["updated_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        ANNOTATIONS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("annotations.json updated")
    else:
        print("no changes")


if __name__ == "__main__":
    main()
