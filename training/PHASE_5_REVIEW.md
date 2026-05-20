# Phase 5 — End-to-end review

**Date:** 2026-05-20
**Reviewer:** integration check + compliance subagent's verdict
**Verdict:** PASS — ready to launch

---

## Employee journey check

| Step | Pass |
|---|---|
| All seven module `.md` files present in `training/modules/` | ✓ |
| Every module has a matching `.questions.json` | ✓ |
| Every bank: ≥ 25 questions, ≥ 10 scenario-tagged, all options/correct/rationale present, stem populated | ✓ |
| Every bank: 2+ reflections (3 on the Manager add-on) with prompts populated | ✓ |
| Question schema uniform across all seven modules (`options` / `correct: int`) after the v1 normalisation pass | ✓ |
| Initial data files (assignments / events / audit / config) all valid JSON | ✓ |
| Employee UI (`/training.html`) compiles cleanly and supports the five-phase flow (cover → read → quiz → reflect → result/cert) | ✓ |

## HR journey check

| Step | Pass |
|---|---|
| Worker exposes every admin endpoint: `admin/state`, `admin/reflections`, `admin/export`, `admin/assign`, `admin/exempt`, `admin/extend`, `admin/escalate`, `admin/auto-enrol`, `admin/reminders` | ✓ |
| `/training-admin.html` calls every endpoint it claims to expose | ✓ |
| Access gate: non-admin viewers see "You don't have admin access" rather than data | ✓ |
| HR can read reflection text only via `/admin/reflections` (KV-backed, never in repo) | ✓ |
| Export tab supports CSV + JSON, file named with date | ✓ |

## Tribunal-evidence journey check

| Step | Pass |
|---|---|
| `trainingSubmitAttempt` appends an `attempt_completed` event with score + question-level detail | ✓ |
| `trainingSaveReflection` appends a `reflection_saved` event (text length only, never the text) | ✓ |
| `trainingCompleteModule` appends a `module_completed` event with the bank version pinned | ✓ |
| `trainingIssueCertificate` appends a `certificate_issued` event with signing officer + module list + next-due date | ✓ |
| Every admin action (`assign` / `exempt` / `extend` / `escalate` / `auto-enrol`) appends to the immutable `training-audit.json` | ✓ |
| Certificate ID format is `TBK-HRT-<year>-<6 alphanum>` and the certificate page is verifiable via URL | ✓ |
| Reflection text storage is in Cloudflare PAYROLL_KV under a prefixed key — **never** in the public GitHub repo | ✓ |

## Compliance verdict (Phase 4 subagent)

PASS WITH CORRECTIONS, all five veto items now addressed:

1. **Module 1 Q15** — option C now correctly says "seven" (not nine) harassment-relevant characteristics.
2. **Module 0 §2** — removed the unverifiable "2024 Bull Express tribunal" citation; replaced with *Forbes v LHR Airport Ltd* [2019].
3. **Module 3 §9 + Q12** — removed the invented "70% acknowledgement" statistic from body, question, rationale, and reflection guidance.
4. **Modules 5 + Manager** — question-bank JSON schema normalised to the modules 0–4 shape so the single quiz renderer works against every bank.
5. **Module 5** — "six routes" inconsistency (heading, closing line, Q11 rationale, reflection r1) all corrected to "seven."

Plus all of the non-veto follow-ups: Module 1 §2 now flags the seven-vs-nine distinction explicitly; Module 0 Q10 rationale re-framed via s.26 + COCON 1.1.7FR; Module 2 §7 long-Covid qualifier added; Module 3 §6 WhatsApp wording softened; Module 4 §2.3 off-site liability correctly framed as already-vicarious-since-2010 with October-2026 tightening; Module 4 §2.6 Policy HR-12 replaced with a generic placeholder; Module Manager §7 stripped the personalised "James at Acme" name; Module 1 + Module 3 reflection guidance aligned with the longer-form Module 0 / 2 wording.

## Final position

The training pack is defensible against EHRC technical-guidance and "all reasonable steps" tribunal review as it stands today. Substantive legal content is statute-cited and current. The Manager add-on materially exceeds the EEOC Task Force benchmark. The bystander framing avoids the Pence-effect frame the PNAS 2019 evidence flags. The October-2026 / 1-September-2026 / 6-April-2026 dates are handled consistently in present / future tense throughout.

**Ship.**

## Outstanding pre-launch operational steps (not blocking software readiness — these are for HR)

1. **HR confirms or publishes the Workplace Relationships policy** referenced in Module 4 §2.6 so the intranet link is live before staff start clicking.
2. **HR sets `TRAINING_LIVE` to `'true'`** in `.github/workflows/training-daily.yml` when ready for real reminder emails. The cron runs dry-run until that flip.
3. **HR sets `HR_ESCALATION_CC`** repository secret to a comma-separated list of HR addresses copied on day-15 escalation emails (optional but recommended).
4. **HR runs the auto-enrolment sweep** from the admin dashboard once — this seeds every active person + line manager with the right module set + deadlines. Until that's run, the system has zero assignments and the dashboard is empty.
5. **HR reads the seven modules.** They'll be fielding questions about the content.
