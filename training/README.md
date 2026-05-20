# Harassment-prevention training — engineering reference

Last touched 2026-05-20. Hand this README to whoever inherits the system.

## What this is

A complete UK-financial-services harassment-prevention training module living inside TogetherBook. Seven modules (0–5 + Manager add-on), 25-question banks, scored attempts, reflections, certificates, admin dashboard, daily reminder mailer, and a tribunal-defensible audit trail.

Built to defend the firm against the **Equality Act 2010 / Worker Protection Act 2023 / Employment Rights Act 2025** "all reasonable steps" lens, with explicit **FCA PS25/23 / COCON 1.1.7FR** alignment for SMCR firms.

## Layout

```
training/
├── README.md                       — this file
├── RESEARCH_SUMMARY.md             — phase 1 synthesis (statutes + evidence + design brief)
├── DESIGN_RATIONALE.md             — phase 2 design + microcopy library
├── COMPLIANCE_REVIEW.md            — phase 4 compliance subagent's findings
├── TEST_PLAN.md                    — phase 5 employee/HR/tribunal walkthrough script
├── HR_BRIEFING.md                  — HR-facing handbook for the admin dashboard
├── reference/
│   ├── module_1_seed.md            — meta notes on the user's Module 1 draft
│   └── module_1_verbatim.md        — the user's original Module 1 (kept as tonal reference)
├── research/
│   ├── 01_uk_legal_framework.md    — Equality Act / WPA / ERA 2025 / EHRC / ACAS / April 2026 reform
│   ├── 02_fca_smcr.md              — PS25/23 / COCON / FIT / SUP / SYSC / Odey
│   ├── 03_provider_audit.md        — Traliant / EVERFI / Skillcast / iHASCO / Marshalls / UCL / Oxford / LSE
│   ├── 04_training_effectiveness.md — Dobbin & Kalev / EEOC Task Force / Bezrukova / BIT / 5Ds
│   └── 05_lms_ux_wcag.md           — Linear/Stripe/Notion patterns + WCAG 2.2 AA criteria
└── modules/                        — module content (.md) + question banks (.questions.json)
    ├── module_0.md                 — Digital channels (Teams/Slack/WhatsApp/email), ~5 min
    ├── module_0.questions.json
    ├── module_1.md                 — The law and why it matters, ~12 min
    ├── module_1.questions.json
    ├── module_2.md                 — Recognising harassment (all 7 protected chars), ~12 min
    ├── module_2.questions.json
    ├── module_3.md                 — Bystander action (5Ds), ~10 min
    ├── module_3.questions.json
    ├── module_4.md                 — Power dynamics + high-risk situations, ~12 min
    ├── module_4.questions.json
    ├── module_5.md                 — Reporting + what happens next, ~10 min
    ├── module_5.questions.json
    ├── module_manager.md           — Manager add-on (mandatory for line managers + SMCR-certified), ~20 min
    └── module_manager.questions.json
```

Data files at repo root (server-managed; do not hand-edit):

```
training-assignments.json    — who is assigned what + deadlines
training-events.json         — append-only audit log of every employee action
training-audit.json          — append-only audit log of every HR/admin action
training-config.json         — cycle config: signing officer, retention, deadline policy
```

Reflection text (sensitive) lives in Cloudflare **PAYROLL_KV** under the prefix `training:reflections:<email>:<module>:<reflection_id>` — never in the repo. Pulled by HR via `/api/training/admin/reflections`.

## Page surface

| URL | Audience | Notes |
|---|---|---|
| `/training.html` | all staff | Employee dashboard + reader + quiz + reflections |
| `/training.html?module=<id>&phase=<x>&section=<n>&q=<i>` | all staff | Resumable URL state |
| `/training-admin.html` | HR / TogetherBook admins | Overview, overdue list, audit log, export, assignment + extension + exemption + escalation modals |
| `/training-cert.html?id=<cert_id>` | certificate holder + HR + tribunal | Single-page certificate view, print-to-PDF, QR-verified |

## Worker endpoints (`/api/training/*`)

All routes Cloudflare-Access-gated. The full table is in `worker/workspace-worker.js` — search for `handleTraining`.

| Method | Path | Audience | Purpose |
|---|---|---|---|
| GET  | `/whoami`            | any signed-in | identity check, is_admin flag |
| GET  | `/state`             | any signed-in | the viewer's assignments + completion + due-dates |
| GET  | `/certificate?id=…`  | self or admin | certificate JSON for the renderer |
| POST | `/start-attempt`     | viewer | mints an attempt; returns 8/10 random questions (no answer key client-side) |
| POST | `/submit-attempt`    | viewer | scores the attempt, logs `attempt_completed`, returns rationales |
| POST | `/save-reflection`   | viewer | stores reflection text in KV; logs `reflection_saved` (metadata only) |
| POST | `/complete-module`   | viewer | once passed + reflections done; logs `module_completed` |
| POST | `/issue-certificate` | viewer | when all assigned modules complete; logs `certificate_issued` |
| GET  | `/admin/state`       | admin | full cohort overview |
| GET  | `/admin/reflections?email=&module=` | admin | reads KV reflection texts (the only path to that data) |
| GET  | `/admin/export?format=csv\|json` | admin | tribunal-ready exports |
| POST | `/admin/assign`      | admin | manual enrolment |
| POST | `/admin/exempt`      | admin | exempt / un-exempt (logged in audit) |
| POST | `/admin/extend`      | admin | per-assignment deadline extension (logged) |
| POST | `/admin/escalate`    | admin | manual mark-as-escalated (mailer respects this) |
| POST | `/admin/auto-enrol`  | admin / cron | sweep people.json for new starters + new line managers |
| POST | `/admin/reminders`   | admin / cron | run today's reminder mailer (worker-side, dry-run by default) |

## Daily cron

`.github/workflows/training-daily.yml` runs **08:30 UTC Mon-Fri** and calls `scripts/training_reminders.py` to (a) auto-enrol new starters + line managers, (b) send today's reminder set (10/5/2/0 days remaining + day-15 escalation).

**The cron runs dry by default.** To enable real email sends:

1. Set the workflow's `TRAINING_LIVE` env to `"true"` (commit the change to `.github/workflows/training-daily.yml` — search for `TRAINING_LIVE`).
2. Make sure the `SMTP_USERNAME` + `SMTP_PASSWORD` repo secrets are populated (the same ones `email-payroll-monthly.yml` already uses).
3. Optionally set the `HR_ESCALATION_CC` secret to a comma-separated list of HR addresses copied on day-15 escalation emails.

The script idempotently logs a `reminder_sent` event for each (user, kind, modules) tuple — re-running the same day is a no-op.

## Question bank rotation

Year-1 vs year-2 vs year-3 should not be the same questions. Two mechanisms:

1. Each `.questions.json` carries a `version` field. The attempt-start event records `bank_version` so a re-published bank can't retroactively change a past attempt.
2. To rotate, add a sibling file `module_X.questions.v2.json`, update the worker to load by version (it currently loads `<id>.questions.json` flat — add a `bank_version` field on the assignment to switch). Year-by-year rotation is a v2 task — the v1 system ships with one bank per module.

## Cycle ownership

`training-config.json` carries:
- `current_cycle_year` — bump on cycle anniversary
- `signing_officer` — CEO name + title + commitment-line (printed on every certificate)
- `retention_years` — default 7
- `reminder_offsets_days` — `[10, 5, 2, 0]`
- `escalation_overdue_days` — `15`
- `modules_all_staff` / `modules_manager_addon` — drives auto-enrol

Edit this file directly to change cycle policy. The admin dashboard reads it on every page load.

## Accessibility

WCAG 2.2 AA aligned. The full implementation checklist is in `DESIGN_RATIONALE.md` §5. Notable:
- `prefers-reduced-motion` honoured on every transition
- All tap targets ≥ 44px on mobile
- `<dfn>`-style glossary on legal terms (TODO — not in v1; deferred to v2 polish)
- Focus rings everywhere; never `outline: none` without replacement
- `role="status"` on all toasts; never focus-shifts during quiz feedback
- No per-question countdown timers (per 2.2.1)

## When something breaks

- The employee page exits gracefully — every failure goes through `toast()` and the page never silently locks up.
- The admin dashboard shows a banner if the viewer isn't admin.
- Worker errors are logged to Cloudflare logs; the worker name is `apifk-workspace-worker2`.
- A `reminder_sent` event with `dry_run: true` means the mailer was in dry-run that day — check the workflow log.
- A 409 race on a JSON write is retried via `updateGhJson` (built into the worker).

## What v2 looks like

Listed in priority order:

1. Rotation: load `module_X.questions.v<n>.json` per `bank_version` on the assignment so year-2 retake gets fresh content automatically.
2. PDF certificate served from the worker (not browser print) — needs a PDFKit-style library in the worker; defer until print-to-PDF is causing friction.
3. SMCR-flag on people.json so the auto-enrol logic targets certified individuals specifically, not just everyone with direct reports. Today's auto-enrol is "is_manager OR has_line_manager_id" — close enough but not exact.
4. Question-flag review queue in the admin dashboard (the `data-flag` button on the quiz UI fires a toast; the event isn't yet persisted to the audit log).
5. Annual report-out: a single export that aggregates disclosure rates / time-to-report / complainant satisfaction (the EEOC metrics in `research/04_training_effectiveness.md` §9).

## Decisions made

- **One bank file per module**, not per-cycle. Rotation is a v2 problem.
- **Reflection texts in KV, not the repo.** Sensitivity matters; we don't want them in the public GitHub mirror.
- **Daily cron is dry-run until HR flips the switch.** Mass-mailing colleagues from a deploy without explicit go-ahead is too risky.
- **Auto-enrol is `is_manager OR is_new_hire`.** Today's data model lacks an SMCR flag; the spec calls for both managers and SMCR-certified individuals to get the Manager add-on, and `is_manager` is the closest proxy.
