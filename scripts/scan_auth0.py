"""
Generate auth0-users.json — the list of active Auth0 accounts in the
`rgcore` tenant (rgcore.auth0.com).

"Active" means: not blocked AND ever logged in. Auth0 accounts created
but never used, or explicitly blocked in the dashboard, are dropped here
so the Directory page only chips people who actually use internal tools.

Required env vars:
  AUTH0_DOMAIN          — e.g. rgcore.auth0.com (no scheme, no trailing slash)
  AUTH0_CLIENT_ID       — Management API M2M app client_id
  AUTH0_CLIENT_SECRET   — Management API M2M app client_secret

Optional:
  OUT — output path (default: auth0-users.json)

The M2M app must be authorized for the Management API with at least the
`read:users` scope. Auth0's default user-list endpoint pages 100 at a
time and caps the offset window at 1000 results; if rgcore has more we
log a warning and surface the cap in the output file's totals.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path


PER_PAGE = 100
MAX_PAGES = 10  # Auth0 caps offset window at 1000 (10 * 100)
OUT_DEFAULT = "auth0-users.json"


def _fail(msg: str) -> "type":
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _http_json(method: str, url: str, *, data: bytes | None = None, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def get_token(domain: str, client_id: str, client_secret: str) -> str:
    body = json.dumps({
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": f"https://{domain}/api/v2/",
        "grant_type": "client_credentials",
    }).encode("utf-8")
    res = _http_json(
        "POST", f"https://{domain}/oauth/token",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    tok = res.get("access_token")
    if not tok:
        _fail(f"no access_token in /oauth/token response: {res}")
    return tok


def list_active_users(domain: str, token: str) -> tuple[list[dict], int | None]:
    """
    Paginate /api/v2/users for non-blocked accounts and keep those that
    have ever logged in. Returns (users, totalReportedByAuth0).
    """
    out: list[dict] = []
    total_reported: int | None = None
    for page in range(MAX_PAGES):
        params = {
            "page": str(page),
            "per_page": str(PER_PAGE),
            "include_totals": "true",
            "search_engine": "v3",
            # Lucene: drop blocked accounts at the API level so we burn
            # the 1000-row offset window on useful rows.
            "q": "(NOT _exists_:blocked) OR blocked:false",
            "fields": ",".join([
                "user_id", "email", "name", "nickname", "username",
                "last_login", "logins_count", "blocked", "email_verified",
                "created_at", "updated_at", "identities",
            ]),
            "include_fields": "true",
        }
        url = f"https://{domain}/api/v2/users?{urllib.parse.urlencode(params)}"
        res = _http_json("GET", url, headers={"Authorization": f"Bearer {token}"})
        users = res.get("users") or []
        if total_reported is None:
            total_reported = res.get("total")
        for u in users:
            if u.get("blocked"):
                continue
            if not u.get("last_login"):
                continue
            out.append({
                "user_id":        u.get("user_id"),
                "email":          (u.get("email") or "").strip().lower(),
                "name":           u.get("name") or "",
                "nickname":       u.get("nickname") or "",
                "last_login":     u.get("last_login"),
                "logins_count":   u.get("logins_count") or 0,
                "email_verified": bool(u.get("email_verified")),
                "created_at":     u.get("created_at"),
                "connections":    sorted({(i or {}).get("connection") for i in (u.get("identities") or []) if i and i.get("connection")}),
            })
        if len(users) < PER_PAGE:
            break
    return out, total_reported


def main() -> None:
    domain = (os.environ.get("AUTH0_DOMAIN") or "").strip()
    client_id = (os.environ.get("AUTH0_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("AUTH0_CLIENT_SECRET") or "").strip()
    if not domain or not client_id or not client_secret:
        _fail("AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET must all be set")
    out_path = Path(os.environ.get("OUT", OUT_DEFAULT))

    print(f"Fetching Management API token for {domain}…", file=sys.stderr)
    token = get_token(domain, client_id, client_secret)

    print("Listing users…", file=sys.stderr)
    users, total_reported = list_active_users(domain, token)
    users.sort(key=lambda u: (u.get("last_login") or ""), reverse=True)

    capped = total_reported is not None and total_reported > MAX_PAGES * PER_PAGE
    doc = {
        "tenant": domain,
        "snapshot_date": _dt.datetime.utcnow().strftime("%Y-%m-%d"),
        "updated_at": _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "definition_of_active": "blocked != true AND last_login is set",
        "totals": {
            "active_users": len(users),
            "auth0_total_reported": total_reported,
            "offset_window_capped": capped,
            "offset_window_max": MAX_PAGES * PER_PAGE,
        },
        "users": users,
    }
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(users)} active users → {out_path}", file=sys.stderr)
    if capped:
        print(
            f"WARNING: Auth0 reports {total_reported} total accounts but the offset window "
            f"caps at {MAX_PAGES * PER_PAGE}. Switch to the export job if this becomes lossy.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
