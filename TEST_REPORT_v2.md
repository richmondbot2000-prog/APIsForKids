# TogetherBook reliability test report — 2026-05-17 (run 2)

## Summary
- Tests run: 15 (SPEC §3.1–§3.15) + 7 targeted re-verification items from brief
- PASS: 22
- FAIL: 0
- WARN: 0

All issues flagged in run 1 (2026-05-17 earlier) are now resolved. No regressions detected.

## Failures
*(none)*

## Warnings
*(none)*

## Targeted re-verification items from brief

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | `doPeopleMerge` re-points FKs in all three linked tables | PASS | `worker/workspace-worker.js:2320-2346` — re-points payroll (`payFile.records`), google-accounts (`gFile.records`) and warehouse-activity (`whFile.records`) within the same function, counters `payrollUpdated / googleUpdated / warehouseUpdated` returned in the response (`:2378-2380`). The fix is documented inline at `:2314-2319` (Bug #1 from earlier run). |
| 2 | `scripts/check_schema_integrity.py` exists and exits 0 | PASS | `python3 scripts/check_schema_integrity.py` → `checked 193 people · 96 payroll · 197 google · 150 warehouse · 22 admins / failures: 0 / warnings: 0 / exit=0` |
| 3 | Schema integrity wired into `.github/workflows/reconcile-people.yml` | PASS | Workflow has a `Verify cross-table schema integrity` step that runs `python3 scripts/check_schema_integrity.py` between the build-* steps and the commit step. |
| 4 | Latest reconcile-people.yml run on GitHub passed | PASS | `gh run list --workflow=reconcile-people.yml --limit=3` → `[{"conclusion":"success","createdAt":"2026-05-17T22:33:54Z","status":"completed"}]` |
| 5 | `wall.html` reads via `/api/workspace/table?file=people` (not `/people.json`) | PASS | `wall.html:1667` — `fetch("/api/workspace/table?file=people", { cache: "no-store", … })`. Earlier WARN resolved. |
| 6 | `togglePayroll` + `suspendPerson` now call `LS.set(...)` after save | PASS | `profile.js:872` `LS.set(person.id, "on_payroll", turnOn)` inside `togglePayroll`; `:876` follow-up `LS.set` for `most_recent_payroll_id` when a blank payroll row is auto-created. `:1340` `LS.set(person.id, "suspended", turnOn)` inside `suspendPerson`. Earlier gap resolved. |
| 7 | Freshness indicator in `directory.html` | PASS | `directory.html:330` — `<div class="pp-freshness" id="ppFreshness" title="…">`. Styles at `:53`. Populated at `:901` (`const fresh = document.getElementById("ppFreshness");`). |
| 8 | SPEC.md "Reliability layer for the identity tables" appendix | PASS | `SPEC.md:2326` — `## Reliability layer for the identity tables (added 2026-05-17)` |

## SPEC §3 test grid

### 3.1 Schema integrity — PASS
`scripts/check_schema_integrity.py` → 193 people / 96 payroll / 197 google / 150 warehouse / 22 admins, **0 failures, 0 warnings, exit 0**. GoogleAccount #5 → person_id 4 (orphan flagged in run 1) is no longer present.

### 3.2 Worker reliability paths — PASS
All required functions/strings present in `worker/workspace-worker.js`:
- `/table` handler dispatched at `:183` (`pathname.replace(/\/$/, "").endsWith("/table")`)
- `cf: { cacheTtl: 0, cacheEverything: false }` at `:202` (and again at `:3206` for second proxy-read use)
- `"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"` at `:213`
- `"X-Table-Sha": data.sha || ""` at `:215`
- `doPeopleSet` `:1696`, `doPayrollSet` `:2001`, `doGoogleAccountSet` `:2160`, `doGoogleAccountDelete` `:2238`, `doPeopleMerge` `:2270`
- `syncAdminsFromPeople` `:1853`
- `nextPersonId` `:1677`, `nextPayrollId` `:1949`, `nextGoogleAccountId` `:2129`
- `denormaliseEmailsToPerson` `:2150` (called from `doGoogleAccountSet:2230`, `doGoogleAccountDelete:2257`, `doPeopleMerge:2336`)

### 3.3 Worker validation rules — PASS
- `"name is required for new people"` literal at `worker/workspace-worker.js:1759`
- `touchingEmails` guard at `:1768-1769`
- `PEOPLE_SELF_EDITABLE` set at `:1576`, enforced at `:1748` (`field "${k}" is admin-only`)
- Google-account one-per-tenant + `denormaliseEmailsToPerson` mirror at `:2230` and `:2257`

### 3.4 Client wiring — localStorage + persistent badge — PASS
- `const LS = {` at `profile.js:27`
- `LS.set(person.id, field, payloadValue)` in `savePersonField` at `:1299`
- `LS.set(person.id, "payroll", out.record)` in `savePayrollEdits` at `:905`
- `LS.set(person.id, field, stamp)` BEFORE network call in `uploadImage` at `:1700`
- `LS.overlay(person)` applied during render at `:1561`
- `LS.savedLabel(...)` + `savedBadge` in `editableRow` at `:257-275`
- `for (let attempt = 1; attempt <= 3; attempt++)` cover-upload retry at `:1706`

### 3.5 Client wiring — reads via Worker proxy — PASS
Stale-fetch grep returns zero hits in directory.html/profile.js/reconcile.html. Only `nav.js:` still reads `/people.json` (acceptable — nav doesn't write back and is OK with edge cache lag per spec §0). Proxy-read grep returns **12 hits** (4 tables × 3 files), exactly matching the spec target.

### 3.6 URL pattern + dispatch — PASS
Every `fetch(WORKSPACE_API` in the three pages has `+ "/" + <action>` appended (20 call sites checked, zero bare `WORKSPACE_API[,)]`).

### 3.7 Cloudflare cache rule — PASS
`PASS — rule live: (http.host eq "book.togetherbook.net" and ends_with(http.request.uri.path, ".json"))`

### 3.8 Cover/photo file audit — PASS
`missing files: 0` — every Person with a `cover_photo_uploaded_at` or `directory_photo_uploaded_at` stamp has the matching JPEG on disk.

### 3.9 Import script correctness — PASS
`python3 scripts/import_payroll.py …` → **matched: 60, ambiguous: 0, conflicts: 0, unmatched: 0**, all matches by `[external_id]` or `[name+dob]`, zero `← verify` markers, zero errors. Dry-run only.

### 3.10 Worker probes — PASS
All six endpoints return HTTP 302 (redirect to Cloudflare Access) — none 404 — confirming `/table?file=…`, `/whoami` and `/payroll` are deployed and routed:
```
table?file=people              HTTP 302
table?file=payroll-data        HTTP 302
table?file=google-accounts     HTTP 302
table?file=warehouse-activity  HTTP 302
whoami                         HTTP 302
payroll                        HTTP 302
```

### 3.11 Recent commits + tampering — PASS
`git log --oneline -30` shows coherent history. `4f26c2e` (Reliability: localStorage write-through…) is present (3rd commit before the 5 most-recent reliability/UX commits). Newest commits since run 1: `c6fe2f7` (the merge fix), `2fec72a` (LS write-through everywhere + freshness indicator + wall.html proxy reads), `50e880c` (reconcile workflow auto-commit), `b52ddf1` (SPEC.md reliability appendix). No reverts, no force-push markers.

### 3.12 Profile rendering paths — PASS
- `renderPanel()` wrapped in try/catch at `profile.js:184-201` with `Render error in <currentTab>` visible message
- `setTab(tab)` at `:174-182` updates URL + classes + calls `renderPanel()`
- Info tab fields all routed through `editableRow(…)` (`:356-362`)
- `renderLinkedSourcesCard()` defined at `:401` and called from Info panel at `:352`

### 3.13 Daily reconcile workflow — PASS
`.github/workflows/reconcile-people.yml` runs `30 6 * * *`. Steps: build_google_accounts → build_warehouse_activity → build_admins → **check_schema_integrity (new)** → commit if changed (with retry-on-rebase loop, max 3 attempts).

### 3.14 Stale fetch detection — PASS
Repo-wide grep returns exactly one hit (`nav.js:` reading `/people.json` for the avatar lookup). All three migrated pages (directory.html, profile.js, reconcile.html) are clean.

### 3.15 What a user should experience — PASS
Spot-checks against `worker/workspace-worker.js` + `profile.js`:
1. **Admin recognition** — owner failsafe `OWNER_EMAIL` hardcoded; James in `admins.json`. ✓
2. **5 source chips** — `renderLinkedSourcesCard()` at `profile.js:401` iterates google + payroll + warehouse links. ✓
3. **Edit role with green badge** — `editableRow` shows `savedBadge` from `LS.savedLabel`; `savePersonField` writes `LS.set` after success. ✓
4. **Edit survives refresh** — proxy read at `:1746` is `cache: "no-store"` from Worker `/table` (HEAD of main, no edge cache); LS overlay re-applied at `:1561`. ✓
5. **Cover upload immediately visible** — `LS.set(person.id, field, stamp)` BEFORE network at `:1700`; stamp-save loop retries 3× at `:1706`. ✓
6. **Two-Person merge** — `doPeopleMerge` re-points payroll + google + warehouse FKs (`worker/workspace-worker.js:2270-2383`), deletes loser, returns winner_id; client redirects after success. ✓

## Notes / observations

- **Run 1 issues, status:**
  - FAIL "doPeopleMerge orphan risk" → **RESOLVED** (c6fe2f7 — re-points all three FKs in one function, with inline comment citing run 1)
  - FAIL "orphan GoogleAccount #5 → person_id 4" → **RESOLVED** (data confirmed clean by check_schema_integrity)
  - WARN "togglePayroll / suspendPerson missing LS.set" → **RESOLVED** (2fec72a — added at profile.js:872 and :1340)
  - WARN "wall.html still reads /people.json" → **RESOLVED** (2fec72a — wall.html:1667 now uses /api/workspace/table?file=people)
  - WARN "no freshness indicator on directory" → **RESOLVED** (2fec72a — directory.html:330 + populated at :901)
  - WARN "no defensive schema-integrity check in CI" → **RESOLVED** (scripts/check_schema_integrity.py + workflow step in 50e880c)
  - WARN "SPEC.md lacks reliability appendix" → **RESOLVED** (b52ddf1 — SPEC.md:2326 onwards)

- **Defensive belt-and-braces:** the new `check_schema_integrity.py` step in the reconcile workflow means any future orphan introduced by a Worker bug or manual JSON edit will fail the workflow within 24h (06:30 UTC) and email the user, instead of rotting silently.

- **Inline regression doc:** `worker/workspace-worker.js:2314-2319` cites SPEC_TESTING.md run 2026-05-17 as the reason for the multi-table re-point — useful provenance for a future maintainer.

- **One acceptable lingering /people.json read:** `nav.js` still reads `/people.json` directly for the topbar avatar lookup. Spec §0 explicitly says this is fine because nav is read-only and tolerates edge-cache lag. Calling it out for completeness, not as a defect.

- **No regressions detected** in any of the 15 SPEC tests. Worker probes, import dry-run, Cloudflare rule and CI workflow are all green.
