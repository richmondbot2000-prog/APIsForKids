# Test plan — Harassment-prevention training

Three walkthrough journeys. Each one has explicit pass criteria. Run before announcing the system to staff.

## Journey 1 — Employee

**Setup:** Admin (you) assigns yourself the all-staff six modules via `training-admin.html` → Assign / extend → Assign a module. Use your own email; pick all six modules; 14-day deadline.

**Walk through:**

1. Open `/training.html`. **Expect:** six cards, each tagged "Due [date]", all with a brass-primary "Start" button.
2. Click "Start" on Module 1. **Expect:** the cover screen. About 12 minutes. No content-warning banner (Module 1 is law, not scenarios).
3. Click "Start the module". **Expect:** Section 1 of 7. Stepper visible. "Saved 14:32" indicator updates as you click "Next section ›".
4. Refresh the page in the middle of Section 3. **Expect:** the page comes back on Section 3 (URL-state restore works).
5. Click through to the test. **Expect:** Question 1 of 8. One question per screen. Scenario badge on the [scenario] questions.
6. Pick wrong answers on purpose for a few; correct on the rest. **Expect:** after the first "Submit answer", the page reveals feedback panels for ALL questions (the worker scores in a single batch). Wrong-answer panel reads "That's not the answer. [statute / rule]. The correct answer is [letter]." Correct-answer panel reads "Correct." (with elaboration on subtle questions).
7. Step backward and forward through the stepper. **Expect:** every question's feedback persists.
8. On Question 8, click "See result". **Expect:** result card, e.g. "You answered 7 of 8 correctly. That's a pass." (if you passed) or "You answered 4 of 8 correctly. The pass mark is 7. You have 2 retakes available."
9. If you failed: click "Try again". **Expect:** new random sample of questions from the bank. Different questions.
10. If you passed: click "Reflection (2 prompts)". **Expect:** two textboxes, each with the "Your manager will not see this" caveat above them.
11. Type a sentence in each. **Expect:** "Saved 14:32" indicator under each as you type.
12. Click "Complete module". **Expect:** dashboard re-renders; Module 1 card shows "Completed" green chip. The next module (Module 0 in alphabetical order or whichever auto-promotion logic picked) is no longer the resume target.
13. Repeat the loop through all six modules.
14. After the last one: **Expect:** dashboard shows the brass cert banner — "You've completed the cycle. Your certificate is below." with an "Issue my certificate" button.
15. Click "Issue my certificate". **Expect:** redirect to `/training-cert.html?id=TBK-HRT-2026-XXXXXX`. The certificate page shows your name, the module list with version stamps, the CEO's signature block, a verification ID at bottom-left, and a "valid until" date one year from issue.
16. Click "Print / save PDF". **Expect:** browser print dialog opens. The print preview drops the chrome (nav, action buttons) and just shows the certificate paper.

**Pass criteria:**
- Saved-at indicator visible at every save point.
- No "Incorrect!" / "Try again!" copy anywhere.
- Reflection caveat appears before the textbox (not inside the placeholder).
- Stepper visible on every reading + quiz screen.
- URL state preserves position on refresh.
- Mobile: all buttons ≥ 44px tall; one question per screen on narrow viewport.

## Journey 2 — HR / Admin

**Setup:** Open `/training-admin.html` as a Cloudflare-Access-authenticated admin.

**Walk through:**

1. Overview tab. **Expect:** every assigned person × module, with status pills. Headline numbers in the cards across the top: People enrolled / Module-assignments / Completed (with %) / Overdue / Escalated / Exempt.
2. Filter by module = "The law" + status = "in progress". **Expect:** the list narrows to anyone partway through Module 1.
3. Click "Extend" on one row. **Expect:** modal opens with a date picker and a reason textbox. Pick a date 14 days from now; type "test extension." Save. **Expect:** the chip changes to the new deadline; the audit log records the action.
4. Click "Exempt" on one row. Type "test exemption". **Expect:** the row's card opacity drops; audit log records it. Click "Re-require" + a reason. **Expect:** the row re-activates.
5. Click "Reflections" on a row where someone has completed the module. **Expect:** modal shows their reflection texts with timestamps. **Pass criteria:** the line-manager of that colleague should NOT be able to see these — verify by checking that the admin dashboard requires admin status (open in a non-admin session, expect the "no access" gate).
6. Overdue tab. **Expect:** anyone past their deadline. If none, leave their assignments alone but visit the tab to confirm the empty state.
7. Click "Escalate" on someone overdue. **Expect:** modal opens; type a note. Save. **Expect:** chip changes to "Escalated"; the daily mailer will stop mailing them.
8. Assign / extend tab → Assign a module. **Expect:** modal with email + module checkboxes + days-until-deadline. Add someone; pick Module 5 + the Manager add-on; 21-day deadline. **Expect:** the new rows appear on Overview.
9. Audit log tab. **Expect:** every action you just took, newest first, with actor email + timestamp + reason.
10. Export tab → Download CSV. **Expect:** a file like `training-export-2026-05-20.csv` with one row per (person, module). Open in Excel — every column present (status, deadline, attempts_used, best_score, completed_at, overdue).
11. Run the auto-enrolment sweep. **Expect:** new assignments for any new starters or new line managers that didn't already have them. The audit log records the sweep with totals.

**Pass criteria:**
- Every action results in a single visible toast confirming success / failure.
- No HR action ever bypasses the audit log.
- Filters survive page navigation within the admin (filter selections persist while you're on Overview; reset is OK on tab switch).

## Journey 3 — Tribunal-evidence walkthrough

Pretend an EHRC investigator asks for evidence the firm met the "all reasonable steps" duty. Walk the chain.

**Walk through:**

1. **Show the policy.** Outside this system — the firm's anti-harassment policy. Verify it's current.
2. **Show the training programme.** Open `training/RESEARCH_SUMMARY.md`. This is the design rationale, traceable to the EHRC 8-step guide. Show §6 (the design decisions) + §7 (the corrections we made before building, including the IFS-misattribution catch).
3. **Show the content.** Open one of the module .md files. Verify it's tonal-adult, scenario-rich, statute-cited.
4. **Show the compliance review.** Open `training/COMPLIANCE_REVIEW.md` (produced by the compliance subagent). This is the firm's record that the content has been independently checked against the law as of 2026-05-20.
5. **Show the records.** Export tab → CSV. Filter to whoever the inquiry is about. Verify: assignment date, deadline, attempts, score, completion date, certificate ID, version of the bank served.
6. **Show the audit log.** Open training-audit.json or the Audit log tab. Verify: every HR action against the subject's record is there with actor + timestamp + reason.
7. **Show the certificate.** Open `/training-cert.html?id=…` for the subject's certificate. Verify: full name (from SSO), date, modules covered with version stamps, signing officer (CEO with commitment line), verification ID, valid-until.
8. **Show the reminder trail.** Search training-events.json for `reminder_sent` events. Verify: the firm tried to reach the subject on the cadence promised (10/5/2/0 days + day-15 escalation to line manager + HR).
9. **Show the manager track.** If the subject was a manager: verify the Manager add-on was auto-enrolled and completed (or escalated).

**Pass criteria:**
- Every step above produces real data (not a TODO or a missing field).
- The audit log shows that no HR action is taken silently — exemptions, extensions and escalations are all documented with reasons.
- The bank version (`bank_version` field on the `attempt_completed` event) matches a real version string — so the firm can show exactly what content was tested on that date.

## Edge cases worth pressing on

- **Network failure mid-quiz.** Disconnect the laptop just after clicking Submit. **Expect:** toast "Couldn't submit: [error]" and the Submit button re-enables. The answer is held client-side.
- **Two tabs open.** Open `/training.html?module=module_1` in two tabs simultaneously and click Submit on different questions. **Expect:** the second tab gets a "attempt expired" error from the worker (the in-flight attempt key in KV is single-use). Refresh resyncs; the second tab can start a new attempt.
- **Re-issuing a certificate after a content rotation.** Mark the existing cert as superseded (currently a manual database edit) and re-issue. **Expect:** new ID. The old one stays in the event log — never deleted.
- **Mobile keyboard.** On the reflection page on iPhone: tap the textarea; verify the page doesn't jump (no fixed-height containers). Type a paragraph. Verify the "Saved" indicator updates as you stop typing.

## What FAILS the test plan

Anything that:
- Drops state on refresh.
- Surfaces an "Incorrect!" / "Try again!" string without rationale.
- Lets a non-admin reach the admin dashboard.
- Lets a line manager read another colleague's reflections.
- Drops a certificate without the CEO signing line and the verification ID.
- Has the auto-enrol fire without an audit-log entry.
- Sends a reminder email outside the dry-run guard when `TRAINING_LIVE` is not set to `"true"`.

If any of those, file an engineering bug before launch.
