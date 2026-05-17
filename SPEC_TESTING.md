# TogetherBook — Reliability & Correctness Testing Spec

This document is a self-contained brief for an agent (or engineer) **with no prior context** to verify that the TogetherBook system behaves correctly, with particular focus on the **identity layer (People + Payroll + Google accounts + Warehouse activity)** and the **read/write reliability guarantees** we've recently put in place.

---

## 0. What you need to know first

**TogetherBook** is an internal dashboard for Richmond Group (Letme, Together Loans). Live at `book.togetherbook.net` (Cloudflare Access gated) + a public mirror at `richmondbot2000-prog.github.io/togetherbook/`. Codebase at `~/Desktop/togetherbook/`.

**No build step.** Plain HTML + CSS + JS files served by GitHub Pages, with a Cloudflare Worker (`apifk-workspace-worker2`) handling write actions (route `book.togetherbook.net/api/workspace/*`).

**Identity model** — four canonical "tables", each a JSON file at the repo root, linked by integer foreign keys:

| File | What it holds | PK | FK |
|---|---|---|---|
| `people.json` | Person records (one per real human) | `id` (integer) | `most_recent_payroll_id` → payroll-data.id; `line_manager_id` → people.id |
| `payroll-data.json` | Payroll records (most recent + historical) | `id` (integer) | `person_id` → people.id |
| `google-accounts.json` | Google accounts linked to Persons | `id` (integer) | `person_id` → people.id |
| `warehouse-activity.json` | Warehouse CRM users | `id` (integer) | `person_id` → people.id |

`url_slug` on People is the human-readable URL form (`/directory/james.benamor`). Google accounts have `tenant` field ∈ `{letme, together, external}`.

**Write path:** Worker actions (admin-only) commit JSON edits via the GitHub Contents API. Each successful action results in a commit on `main`.

**Read path:**
- **Mutable tables** (the four above) — read via `GET /api/workspace/table?file=<name>`. The Worker fetches via GitHub Contents API at HEAD of main → bypasses GitHub Pages publish lag AND Cloudflare edge cache. This is the **canonical read** and must be used for any view where freshness matters.
- **Static tables** (staff.json, wall.json, holidays.json etc.) — read directly via `/<file>.json`. Acceptable lag because these are refreshed on a schedule, not by user edits.

**Two-layer reliability guarantee for writes:**
1. **Worker proxy reads** (server-side) — eliminate GitHub Pages publish lag and Cloudflare edge cache.
2. **localStorage write-through + persistent ✓ badge** (client-side) — every saved field is mirrored to `localStorage` keyed by `tbk.edit.<personId>.<field>` with a 5-min TTL, overlaid on render. Visible green "✓ Saved HH:MM" badge next to any field with an unexpired entry. Means the user's own session can never appear to "lose" an edit even if the server response is lost mid-flight.

---

## 1. Your mission

Verify that:
1. The canonical tables are internally consistent (no broken FKs, no missing required fields, no impossible states).
2. The Worker code paths for reads + writes match the spec.
3. The client code (profile.js, directory.html, reconcile.html) actually wires through the reliability layer.
4. Recent fixes haven't regressed prior functionality.

Report findings in a single Markdown summary at the end. For every test: **PASS / FAIL / WARN** with one line of evidence.

You **cannot** browse the live site (Cloudflare Access blocks anonymous requests). You **can** read code, run scripts, inspect JSON files, check git history, and probe Worker endpoints to verify they return the expected error shapes.

---

## 2. Environment + tools

- Working dir: `~/Desktop/togetherbook/`
- `git`, `python3`, `curl`, `jq` all available
- All JSON files at the repo root are readable
- Worker source: `worker/workspace-worker.js`
- Profile renderer: `profile.js` (shared by `user.html` + `404.html`)
- Directory page: `directory.html`
- Reconcile page: `reconcile.html`
- Import scripts: `scripts/*.py`
- Spec docs: `SPEC.md` (long-form), `CLAUDE.md` (working-style notes — ignore unless you want context)

---

## 3. Tests

### 3.1 Schema integrity (run a single Python script)

Write a Python check that loads all four tables + verifies:

| Check | Expectation |
|---|---|
| **people.json** | every Person has `id` (int), `url_slug` (string), `name` (non-empty string) |
| **people.json** | every `url_slug` is unique across all Persons |
| **people.json** | every `id` is unique and a positive integer |
| **people.json** | every `most_recent_payroll_id`, when non-null, resolves to a real payroll-data.id |
| **people.json** | every `line_manager_id`, when non-null, resolves to a real people.id (and not self) |
| **payroll-data.json** | every record's `person_id` resolves to a real people.id (or is null) |
| **google-accounts.json** | every record's `person_id` resolves to a real people.id (or is null) |
| **google-accounts.json** | tenant ∈ {letme, together, external} on every row |
| **warehouse-activity.json** | every record's `person_id`, when non-null, resolves to a real people.id |
| **admins.json** | every email in `admins` corresponds to a Person in people.json with `access_level=admin` and `!suspended`, OR the owner failsafe (`james.benamor@letme.com`) |

Suggested script:
```bash
cd ~/Desktop/togetherbook && python3 - <<'PY'
import json, pathlib, sys
P = lambda f: json.loads(pathlib.Path(f).read_text())
ppl  = P("people.json")["people"]
pay  = P("payroll-data.json")["records"]
gacc = P("google-accounts.json")["records"]
wh   = P("warehouse-activity.json")["records"]
adm  = P("admins.json").get("admins", [])

failures = []
seen_ids = set(); seen_slugs = set()
for p in ppl:
    if not isinstance(p.get("id"), int) or p["id"] <= 0: failures.append(f"bad id on Person {p}")
    if p["id"] in seen_ids: failures.append(f"duplicate Person id {p['id']}")
    seen_ids.add(p["id"])
    slug = p.get("url_slug")
    if not slug: failures.append(f"Person #{p['id']} missing url_slug")
    elif slug in seen_slugs: failures.append(f"duplicate url_slug {slug}")
    seen_slugs.add(slug)
    if not (p.get("name") or "").strip(): failures.append(f"Person #{p['id']} has empty name")
people_ids = seen_ids
pay_ids = set(r["id"] for r in pay)
for p in ppl:
    mrid = p.get("most_recent_payroll_id")
    if mrid is not None and mrid not in pay_ids:
        failures.append(f"Person #{p['id']} most_recent_payroll_id={mrid} → no payroll record")
    lm = p.get("line_manager_id")
    if lm is not None and lm != "" and lm not in people_ids:
        failures.append(f"Person #{p['id']} line_manager_id={lm} → no Person")
    if lm == p.get("id"):
        failures.append(f"Person #{p['id']} is its own line_manager")
for r in pay:
    if r.get("person_id") is not None and r["person_id"] not in people_ids:
        failures.append(f"PayrollData #{r['id']} person_id={r['person_id']} → no Person")
for g in gacc:
    if g.get("person_id") is not None and g["person_id"] not in people_ids:
        failures.append(f"GoogleAccount #{g['id']} person_id={g['person_id']} → no Person")
    if g.get("tenant") not in ("letme","together","external"):
        failures.append(f"GoogleAccount #{g['id']} bad tenant={g.get('tenant')}")
for w in wh:
    if w.get("person_id") is not None and w["person_id"] not in people_ids:
        failures.append(f"WarehouseActivity #{w['id']} person_id={w['person_id']} → no Person")

admin_emails = set()
for p in ppl:
    if p.get("access_level") == "admin" and not p.get("suspended"):
        if p.get("main_google_email"): admin_emails.add(p["main_google_email"].lower())
        for e in (p.get("alt_google_emails") or []):
            if e: admin_emails.add(e.lower())
admin_emails.add("james.benamor@letme.com")  # owner failsafe
for e in adm:
    if e.lower() not in admin_emails:
        failures.append(f"admins.json contains {e} but people.json doesn't mark them admin")

print(f"checked {len(ppl)} people, {len(pay)} payroll, {len(gacc)} google, {len(wh)} warehouse, {len(adm)} admins")
print(f"failures: {len(failures)}")
for f in failures[:30]: print(" ", f)
sys.exit(1 if failures else 0)
PY
echo "exit=$?"
```

### 3.2 Worker reliability paths exist (grep the source)

Verify these are present in `worker/workspace-worker.js`:

| Endpoint / function | What to grep for | Why |
|---|---|---|
| `GET /api/workspace/table?file=<name>` | `pathname.replace(...).endsWith("/table")` | This is the canonical-read endpoint that bypasses publish lag + cache |
| `cf: { cacheTtl: 0, cacheEverything: false }` | exact string in /table handler | Forces Cloudflare not to cache GitHub Contents API responses |
| `Cache-Control: no-store, no-cache, must-revalidate` | in /table response headers | Forces clients not to cache responses |
| `X-Table-Sha` | response header from /table | Lets clients verify which SHA they're reading from |
| `doPeopleSet` | function definition | Worker action that writes Person updates |
| `doPayrollSet` | function definition | Worker action that writes PayrollData updates |
| `doGoogleAccountSet` / `doGoogleAccountDelete` | function definitions | Google account CRUD |
| `doPeopleMerge` | function definition | Two-Person merge logic |
| `syncAdminsFromPeople` | function | Regenerates admins.json from people.json access_level field |
| `nextPersonId` / `nextPayrollId` / `nextGoogleAccountId` | function names | Integer-PK generators (max+1) |
| `denormaliseEmailsToPerson` | function | Keeps people.json email fields in sync when google-accounts changes |

For each function/string above, confirm it exists. Note any that are missing.

### 3.3 Worker validation rules (grep + check logic)

Verify in `doPeopleSet`:
- Name required on create (look for `name is required for new people`)
- One Google account per tenant rule, but **only fires when patch touches email fields** (look for the `touchingEmails` guard)
- Self-edit carve-out: when actor matches a Google account on the Person, restricted to `PEOPLE_SELF_EDITABLE` fields
- Auto-create blank payroll record when `on_payroll` flips to true and `most_recent_payroll_id` is null

Verify in `doGoogleAccountSet`:
- One-per-tenant rule
- Mirrors changes back to people.json email fields (look for `denormaliseEmailsToPerson` call)
- Returns updated person + record

### 3.4 Client wiring — localStorage + persistent badge (grep profile.js)

Confirm in `profile.js`:

| Check | Expected |
|---|---|
| `const LS = {` helper defined | yes |
| `LS.set(person.id, field, payloadValue)` called in `savePersonField` after successful save | yes |
| `LS.set(person.id, "payroll", out.record)` called in `savePayrollEdits` after success | yes |
| `LS.set(person.id, field, stamp)` called BEFORE the network call in `uploadImage` | yes |
| `LS.overlay(person)` applied during `renderProfile()` | yes |
| `LS.savedLabel(person.id, field)` produces "Saved HH:MM" used in `editableRow` | yes — look for `savedBadge` |
| Cover/avatar upload retries on stamp-save up to 3 times | yes — `for (let attempt = 1; attempt <= 3` in `uploadImage` |

### 3.5 Client wiring — reads via Worker proxy (grep)

Confirm in `directory.html`, `profile.js`, `reconcile.html` that:
- `fetch("/api/workspace/table?file=people"` is present (for people.json read)
- `fetch("/api/workspace/table?file=payroll-data"` (or similar) for payroll-data
- `fetch("/api/workspace/table?file=google-accounts"` for google-accounts
- `fetch("/api/workspace/table?file=warehouse-activity"` for warehouse-activity
- **No** lingering `fetch("/people.json"` (without query) should remain — that would be the old cache-vulnerable read path

Quick command:
```bash
cd ~/Desktop/togetherbook && grep -nE 'fetch\("/people\.json|fetch\("/payroll-data\.json|fetch\("/google-accounts\.json|fetch\("/warehouse-activity\.json' directory.html profile.js reconcile.html
# Should return zero hits.
grep -nE 'fetch\("/api/workspace/table\?file=' directory.html profile.js reconcile.html | head
# Should return 12+ hits (4 tables × 3 files).
```

### 3.6 URL pattern + dispatch (grep)

The Worker reads `action` from the URL path, not the body. Confirm:

- Every `fetch(WORKSPACE_API` in profile.js / directory.html / reconcile.html has an action appended:
  ```bash
  grep -nE 'fetch\(WORKSPACE_API[, )]' directory.html profile.js reconcile.html
  # Expect: zero hits (all should be WORKSPACE_API + "/<action>")
  ```

### 3.7 Cloudflare Cache Rule still live

```bash
cd ~/Desktop/togetherbook && python3 - <<'PY'
import json, pathlib, urllib.request, urllib.error
cfg = json.loads((pathlib.Path.home() / ".togetherbook" / "cloudflare.json").read_text())
ZONE = "fb7983258eeb24f2c199b2f9d0a1a236"
def cf(p):
    r = urllib.request.Request(f"https://api.cloudflare.com/client/v4{p}")
    r.add_header("Authorization", f"Bearer {cfg['api_token']}")
    try:
        with urllib.request.urlopen(r) as resp: return json.loads(resp.read())
    except urllib.error.HTTPError as e: return json.loads(e.read())
out = cf(f"/zones/{ZONE}/rulesets")
rs = next((r for r in out.get("result", []) if r.get("phase") == "http_request_cache_settings"), None)
if not rs: print("FAIL: no cache-settings ruleset"); raise SystemExit(1)
rs_full = cf(f"/zones/{ZONE}/rulesets/{rs['id']}")
rule = next((r for r in rs_full["result"].get("rules", []) if "book.togetherbook.net" in r.get("expression","")), None)
if not rule: print("FAIL: no rule for book.togetherbook.net"); raise SystemExit(1)
if rule.get("action_parameters", {}).get("cache") is not False: print(f"FAIL: rule action is not bypass cache: {rule['action_parameters']}"); raise SystemExit(1)
if not rule.get("enabled"): print("FAIL: rule disabled"); raise SystemExit(1)
print(f"PASS — rule live: {rule['expression']}")
PY
```

### 3.8 Cover photo files vs Person stamps (audit)

For each Person with `cover_photo_uploaded_at` set, verify the corresponding file exists at `assets/covers/<email>.jpg` where `<email>` has `@` replaced with `_at_`.

For each Person with `directory_photo_uploaded_at` set OR an annotation with same, verify `assets/photos/<email>.jpg` exists.

```bash
cd ~/Desktop/togetherbook && python3 - <<'PY'
import json, pathlib
ppl = json.loads(pathlib.Path("people.json").read_text())["people"]
ann = json.loads(pathlib.Path("annotations.json").read_text())["annotations"]
missing = []
def keys(p):
    out = []
    for e in [p.get("main_google_email"), *(p.get("alt_google_emails") or []), p.get("external_google_email")]:
        if e: out.append(e.lower())
    return out
for p in ppl:
    if p.get("cover_photo_uploaded_at"):
        emails = keys(p)
        found = False
        for e in emails:
            if pathlib.Path(f"assets/covers/{e.replace('@','_at_')}.jpg").exists():
                found = True; break
        if not found and emails:
            missing.append(f"Person #{p['id']} ({p['name']}) has cover_photo_uploaded_at but no file in assets/covers/")
    # Check directory photo: stamp can be on Person OR on annotations.
    stamps = set()
    if p.get("directory_photo_uploaded_at"): stamps.add(p["directory_photo_uploaded_at"])
    for e in keys(p):
        a = ann.get(e, {})
        if a.get("directory_photo_uploaded_at"): stamps.add(a["directory_photo_uploaded_at"])
    if stamps:
        emails = keys(p)
        found = any(pathlib.Path(f"assets/photos/{e.replace('@','_at_')}.jpg").exists() for e in emails)
        if not found and emails:
            missing.append(f"Person #{p['id']} ({p['name']}) has directory_photo stamp but no file in assets/photos/")
print(f"missing files: {len(missing)}")
for m in missing[:15]: print(" ", m)
PY
```

Note: a missing file is a soft failure (image won't display), not data corruption.

### 3.9 Import script correctness

Run a dry-run import using the same payroll files used today:

```bash
cd ~/Desktop/togetherbook && python3 scripts/import_payroll.py \
  "/Users/richmondrobot/Desktop/wiki/payroll/For James EmployeeDetails-20260512 (1).xlsx - Export.csv" \
  "/Users/richmondrobot/Desktop/wiki/payroll/LetMe_Property_Management_Limited_-_Employee_Contact_Details.xlsx - Employee Contact Details.csv"
```

Expected:
- 60 matched, 0 ambiguous, 0 conflicts, 0 unmatched
- Match kinds mostly `[external_id]` and `[name+dob]` — no `[name "← verify"]` for these files
- No errors

### 3.10 Worker probes (curl from terminal — auth-gated)

Hitting Worker endpoints from terminal will be redirected to Cloudflare Access login (302/HTML). That's expected behaviour. What you want to verify is that the endpoints **exist** (not 404) and respond:

```bash
for path in "table?file=people" "table?file=payroll-data" "table?file=google-accounts" "table?file=warehouse-activity" "whoami" "payroll"; do
  echo "--- /api/workspace/$path ---"
  curl -s -o /dev/null -w "  HTTP %{http_code} → final: %{redirect_url}\n" \
    "https://book.togetherbook.net/api/workspace/$path" --max-redirs 0
done
```

Expected: every endpoint returns 302 (redirect to Cloudflare Access). A 404 on any of `table?file=…` means the Worker endpoint isn't deployed.

### 3.11 Recent commits + tampering check

```bash
cd ~/Desktop/togetherbook && git log --oneline -30 | head -30
```

The most recent ~10 commits should look coherent (no unexplained reverts, no "Initial commit"-style anomalies, no force-push markers in reflog).

Spot-check: is `4f26c2e` (the "Reliability: localStorage write-through…") commit present? It should be the most recent or near-most-recent.

### 3.12 Profile page rendering paths (read profile.js)

Read `profile.js` and verify:
- `renderPanel()` has try/catch around the panel dispatch so a tab render error doesn't leave the previous tab visible (look for `Render error in ${currentTab}`)
- `setTab(tab)` updates URL + classes + calls `renderPanel`
- Every editable field on Info tab uses `editableRow(field, …)` so they're all covered by the saved-badge logic
- The Info tab renders `renderLinkedSourcesCard()` which shows each linked source with its identifier

### 3.13 Daily reconcile workflow exists

```bash
cd ~/Desktop/togetherbook && cat .github/workflows/reconcile-people.yml
```

Expected: workflow runs at `30 6 * * *` (daily 06:30 UTC), runs build_google_accounts.py + build_warehouse_activity.py + build_admins.py, commits any drift.

### 3.14 Stale fetch path detection

This is the most important regression check. Search for ANY fetch in the JS/HTML that bypasses the proxy-read endpoint for the four canonical tables:

```bash
cd ~/Desktop/togetherbook && grep -rE 'fetch\([^)]*(?:people|payroll-data|google-accounts|warehouse-activity)\.json' --include="*.html" --include="*.js" . | grep -v node_modules
```

Expected zero hits in `directory.html`, `profile.js`, `reconcile.html` (the three pages we migrated). Hits in OTHER files (build scripts, nav.js, etc.) need individual judgement — nav.js doesn't read these tables and is fine; scripts read locally not via worker and are fine.

### 3.15 What a user should EXPERIENCE (verify by reading code)

A user signing in as `james.benamor@letme.com` should:

1. **Be recognised as admin.** Worker `/api/workspace/whoami` returns `is_admin: true`. (Confirmed by: he's in `admins.json` AND he's the hardcoded `OWNER_EMAIL`.)
2. **See all 5 source icons on his Directory row.** People.json #91 has main email letme.com + alt togetherloans + the photo stamp + linked payroll = all chips lit.
3. **Be able to edit his role from the Info tab.** Click Edit → type → click Save → green ✓ badge "Saved HH:MM" appears next to ROLE label → the value displays.
4. **After page refresh, edit must still appear.** The Worker proxy reads ensure people.json's `role` is read at HEAD-of-main (no cache, no publish lag). PLUS the localStorage TTL keeps the user's own edit visible for 5 minutes even if a layer hiccups.
5. **Upload a cover photo and see it immediately.** The `assets/covers/james.benamor_at_letme.com.jpg` file is written by the first Worker call. The second call retries up to 3× to stamp `cover_photo_uploaded_at`. localStorage gets the new stamp BEFORE the network call so the new image URL renders immediately on this device regardless of stamp-write success.
6. **Merge two Person records via the Info tab "Merge this Person" card.** Worker re-points payroll records, deletes loser, redirects to winner. The 5 source icons consolidate.

For each of (1)–(6), read the relevant code in `worker/workspace-worker.js` and `profile.js` and confirm the implementation matches the described behaviour. Note any gap between spec and code.

---

## 4. Report format

Output a single Markdown summary with this shape:

```
# TogetherBook reliability test report — <date>

## Summary
- Tests run: <n>
- PASS: <n>
- FAIL: <n>
- WARN: <n>

## Failures
- [3.1 schema] <evidence>
- [3.5 stale fetch] <evidence>
...

## Warnings
- [3.8 cover photo files] 2 Persons have stamp without file
...

## Notes / observations
- Anything else you noticed worth flagging
```

Be specific. "PASS — 0 broken FKs across 204 Persons / 96 payroll / 196 google-accounts / 150 warehouse rows" is useful; "Looks OK" is not.

---

## 5. Out of scope for this run

- Live browser testing (no auth available)
- Mobile UI testing
- Cross-tenant Google Workspace API calls (no Google service account credentials available outside the Worker)
- Load testing / performance
- Wall posts, holidays, brokers, pipeline, comms — those are separate concerns and don't share the identity tables' reliability story
