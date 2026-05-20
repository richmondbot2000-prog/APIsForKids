#!/usr/bin/env python3
"""One-shot backfill: link every Person in people.json to BookR users.

For each Person, collect every confident BookR match (score >= min) by
walking candidate emails (main_google_email + alts + external_google_email)
against /users/<uid>.email in the rg-bookr Firebase Realtime DB. The full
set is stored in Person.bookr_uids (array). Legacy singular bookr_uid is
dropped from each row as it is rewritten.

With --create, Persons with zero candidates at any score and no existing
link mint a fresh BookR user via POST /users.json (Firebase returns the
new push key) seeded with the Person's email + name + phone (mobile
defaults to "0" to satisfy BookR's existing reads).

Idempotent: existing uids that still resolve in /users are preserved.
Uids that no longer exist in /users are dropped as stale.

Note on push-key uids: BookR's mobile app authenticates via Firebase Auth
and looks up the signed-in user by their Auth uid, so a TogetherBook-
minted record (push-key uid) can be *booked for* but cannot be *signed
in as* until a Firebase Auth account is provisioned for that email
separately. The historical native flow auto-creates that on first sign-in.

Triggered manually from GitHub Actions UI; never runs on a schedule.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BOOKR_DB_URL = "https://rg-bookr.firebaseio.com"
PEOPLE_JSON_PATH = Path("people.json")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def get_bookr_access_token() -> str:
    """Service-account JWT bearer grant against oauth2.googleapis.com.
    Mirrors worker getBookrAccessToken(). Returns a 1h access token."""
    raw = os.environ.get("BOOKR_SERVICE_ACCOUNT_JSON")
    if not raw:
        raise SystemExit("BOOKR_SERVICE_ACCOUNT_JSON env var is required")
    sa = json.loads(raw)
    if not sa.get("client_email") or not sa.get("private_key"):
        raise SystemExit("BOOKR_SERVICE_ACCOUNT_JSON missing client_email / private_key")
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT", "kid": sa.get("private_key_id")}
    claims = {
        "iss": sa["client_email"],
        "aud": "https://oauth2.googleapis.com/token",
        "scope": "https://www.googleapis.com/auth/firebase.database "
                 "https://www.googleapis.com/auth/userinfo.email",
        "iat": now,
        "exp": now + 3600,
    }
    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    c = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{h}.{c}"

    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    sig = key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    jwt = f"{signing_input}.{_b64url(sig)}"

    body = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt,
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]


def bookr_fetch(token: str, path: str, method: str = "GET", body=None):
    url = f"{BOOKR_DB_URL}{path}"
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}access_token={urllib.parse.quote(token)}"
    headers = {}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        raw = resp.read()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw.decode()


def candidate_emails(person: dict) -> list:
    out = [person.get("main_google_email"), person.get("external_google_email")]
    out.extend(person.get("alt_google_emails") or [])
    return [(e or "").strip().lower() for e in out if e]


import re

def _norm_name(s):
    s = (s or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def _email_local(e):
    e = (e or "").strip().lower()
    at = e.find("@")
    return e[:at] if at > 0 else ""

def score_match(person, bookr):
    b_email = (bookr.get("email") or "").strip().lower()
    b_name  = _norm_name(bookr.get("name"))
    p_emails = candidate_emails(person)
    if b_email and b_email in p_emails:
        return 100
    b_local = _email_local(b_email)
    if b_local and any(_email_local(e) == b_local for e in p_emails):
        return 80
    p_name = _norm_name(person.get("name"))
    p_given = _norm_name(person.get("given") or "")
    p_fam   = _norm_name(person.get("family") or "")
    if p_name and b_name and p_name == b_name:
        return 60
    if p_given and p_fam and p_given in b_name and p_fam in b_name:
        return 40
    return 0

def person_bookr_uids(p):
    arr = p.get("bookr_uids")
    if isinstance(arr, list):
        return [x.strip() for x in arr if isinstance(x, str) and x.strip()]
    legacy = p.get("bookr_uid")
    if isinstance(legacy, str) and legacy.strip():
        return [legacy.strip()]
    return []


def main() -> int:
    allow_create = "--create" in sys.argv
    min_score = 80
    for a in sys.argv[1:]:
        if a.startswith("--min-score="):
            try: min_score = int(a.split("=", 1)[1])
            except: pass
    if not PEOPLE_JSON_PATH.exists():
        raise SystemExit(f"missing {PEOPLE_JSON_PATH} -- run from repo root")
    token = get_bookr_access_token()
    bookr_users = bookr_fetch(token, "/users.json") or {}
    print(f"loaded {len(bookr_users)} BookR users (allow_create={allow_create}, min_score={min_score})", flush=True)
    file = json.loads(PEOPLE_JSON_PATH.read_text())
    people = file.get("people") or []
    counts = {"added": 0, "created": 0, "already_linked": 0,
              "needs_review": 0, "no_candidates": 0, "stale_dropped": 0,
              "skipped_no_email": 0, "errored": 0, "people_touched": 0}
    rows = []
    for p in people:
        pid = p.get("id")
        name = p.get("name") or p.get("url_slug") or f"#{pid}"
        existing = person_bookr_uids(p)
        # Drop stale existing uids no longer in /users.
        live = [u for u in existing if u in bookr_users]
        stale = [u for u in existing if u not in bookr_users]
        # Rank every candidate.
        ranked = []  # (score, uid)
        for uid, u in bookr_users.items():
            sc = score_match(p, u or {})
            if sc > 0:
                ranked.append((sc, uid))
        ranked.sort(key=lambda x: -x[0])
        confident = [uid for (sc, uid) in ranked if sc >= min_score]
        union = list(live)
        added = []
        for uid in confident:
            if uid not in union:
                union.append(uid)
                added.append(uid)
        legacy_present = "bookr_uid" in p
        changed = (set(union) != set(existing)) or legacy_present
        status_parts = []
        if added:
            status_parts.append(f"added={len(added)}")
            counts["added"] += len(added)
        if stale:
            status_parts.append(f"stale_dropped={len(stale)}")
            counts["stale_dropped"] += len(stale)
        # Decide if creation is appropriate.
        if not union and not ranked and allow_create:
            primary = (p.get("main_google_email") or (candidate_emails(p) or [""])[0]).strip()
            if not primary:
                counts["skipped_no_email"] += 1
                rows.append((pid, name, "skipped_no_email", 0, ""))
                continue
            try:
                new = bookr_fetch(token, "/users.json", method="POST", body={
                    "email": primary, "name": p.get("name") or "",
                    "mobile": p.get("phone") or "0", "last_online": 0, "suspended": False,
                })
                new_uid = (new or {}).get("name")
                if not new_uid: raise RuntimeError("Firebase POST returned no push key")
                bookr_users[new_uid] = {"email": primary, "name": p.get("name") or ""}
                union.append(new_uid)
                added.append(new_uid)
                counts["created"] += 1
                status_parts.append("created")
                changed = True
            except Exception as exc:
                counts["errored"] += 1
                rows.append((pid, name, f"errored:{exc}", 0, ""))
                continue
        # Categorise the outcome for the summary count.
        if not added and not stale:
            if union:
                counts["already_linked"] += 1
                if not status_parts:
                    status_parts.append("already_linked")
            elif ranked and ranked[0][0] < min_score:
                counts["needs_review"] += 1
                status_parts.append(f"needs_review(top={ranked[0][0]})")
            else:
                counts["no_candidates"] += 1
                status_parts.append("no_candidates")
        # Write back if anything actually changed.
        if changed:
            counts["people_touched"] += 1
            p["bookr_uids"] = union
            if "bookr_uid" in p:
                del p["bookr_uid"]
        rows.append((pid, name, ",".join(status_parts) or "noop",
                     ranked[0][0] if ranked else 0,
                     ";".join(union)))
    file["people"] = people
    PEOPLE_JSON_PATH.write_text(json.dumps(file, indent=2) + "\n")
    print()
    print(f"{'pid':>5}  {'name':<28}  {'status':<36}  {'top':>3}  bookr_uids")
    print("-" * 110)
    for pid, name, status, sc, uids in rows:
        print(f"{pid!s:>5}  {name[:28]:<28}  {status[:36]:<36}  {sc:>3}  {uids}")
    print()
    print(f"summary: people_touched={counts['people_touched']} added={counts['added']} "
          f"already_linked={counts['already_linked']} created={counts['created']} "
          f"stale_dropped={counts['stale_dropped']} "
          f"needs_review={counts['needs_review']} no_candidates={counts['no_candidates']} "
          f"skipped_no_email={counts['skipped_no_email']} errored={counts['errored']}")
    return 0 if counts["errored"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
