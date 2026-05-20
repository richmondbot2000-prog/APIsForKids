# HR briefing — Harassment-prevention training

For the HR colleague who runs the day-to-day. Read once before launch; refer back as needed.

## The dashboard

Open `book.togetherbook.net/training-admin.html`. You need to be a TogetherBook admin — the system checks Cloudflare Access automatically. If you see "You don't have admin access," ping engineering.

Five tabs across the top:

- **Overview** — every person × every module, filterable. Per-row buttons for extend / exempt / reflections.
- **Overdue** — anyone whose deadline has passed without completion. Per-row extend / escalate.
- **Assign / extend** — bulk action buttons (assign a single person ad-hoc; run the auto-enrolment sweep).
- **Audit log** — every action HR has taken on training records. Immutable.
- **Export** — CSV (for spreadsheets / tribunal) + JSON (for engineering / forensic review).

## The first launch

1. **Read the modules.** All seven sit in `training/modules/*.md`. Aim to read every one — you'll be the person fielding questions.
2. **Make sure the signing officer is right.** Open `training-config.json` in the repo. The `signing_officer` block is what appears on every certificate. Default is James Benamor, Group CEO. Edit if the firm wants someone else on it.
3. **Run the auto-enrolment sweep** (Overview → "Run auto-enrolment sweep"). This pulls people.json and assigns:
   - **Every employee** the six all-staff modules (0, 1, 2, 3, 4, 5) — except those flagged as suspended.
   - **Every line manager** the Manager add-on.
   - New starters (hired within the last 14 days) get the longer 30-day deadline; everyone else gets 14 days.
4. **Skim the resulting list.** Anyone obviously wrong (contractor wrongly enrolled, executive on long-term leave) can be exempted via the per-row Exempt button. Every exemption is logged in the audit trail with the reason you type.
5. **Flip the email mailer to live.** By default the daily cron runs in dry-run — it logs what it would send but doesn't actually email anyone. When you're ready:
   - Open `.github/workflows/training-daily.yml`
   - Change `TRAINING_LIVE` to `'true'`
   - Commit. The next 08:30 UTC run sends real email.
   - Until that flip, you can preview what the mailer would do by running the workflow manually (Actions → "Training reminders + auto-enrol" → "Run workflow") with `live=false` (the default). The job log shows every email + recipient.

## Day-to-day actions

### Someone is on leave / parental leave

1. Find them in Overview.
2. Click **Exempt** on each module they're not expected to complete.
3. Add the reason ("on maternity leave, due back 12 Sept").
4. **When they're back**, find them again (filter by status = exempt). Click **Re-require** with reason "back from leave."
5. The system will not auto-reset the deadline — you may want to **Extend** to a sensible date once re-required.

### Someone missed the deadline

1. Day 15 escalation fires automatically — their line manager + HR (you, if `HR_ESCALATION_CC` is set) get an email.
2. If they have a legitimate reason (illness, sudden travel), click **Extend** on the Overdue tab and pick a new date. The system records the extension in the audit trail.
3. If they're stalling, click **Escalate** to record that you've taken a manual action. The mailer respects the escalation flag and stops mailing the colleague (so they're not double-nagged after you've spoken to them).

### Someone fails three times

The system auto-locks them out after the third failed attempt and writes an `escalation_attempt_budget` event. They see "HR has been notified" on the dashboard.

What to do:
1. Schedule a one-to-one.
2. Walk them through the module section by section (the page supports skipping the test for HR-assisted resits — TODO this is v2; for v1, manually exempt + re-require after the conversation).
3. If repeated failures suggest disengagement that's a wider conduct issue, document it. Under SMCR, a failure to engage with required culture training can itself be relevant.

### Reading reflections

Reflections are open-text answers the colleague writes after passing each module. They're held in private (Cloudflare KV, not the repo). Only HR admins can read them.

To read:
1. Overview tab → find the person × module → click **Reflections**.
2. The dialog shows both prompts and the answers they wrote, with the timestamp.

**Treat these as confidential.** The promise to the colleague is "your manager won't see this — it's for your own reflection." Don't quote them back at the colleague, don't reference them in performance conversations, don't surface them to their line manager. Use them as a barometer of cultural distance — patterns across the firm tell you something the completion rate doesn't.

### Compliance evidence (tribunal / EHRC request)

1. Export tab → Download CSV. This is what most tribunal solicitors will ask for.
2. The JSON export includes the full event log — every attempt, every question/answer pair, every reflection metadata entry (not the text), every certificate.
3. The audit log (Audit log tab) is the immutable record of HR actions — useful for "the firm took XYZ steps in response to YZ event" claims.

## What counts as "all reasonable steps"

The tribunal lens from October 2026 will weigh:

1. **The training was delivered, to whom, and how recently.** This system gives you exactly that.
2. **The training was substantive.** Not tick-box. Each module is 25-question-banked, scenario-weighted, with the FCA SMCR layer wired in.
3. **Reporting routes were taught and tested.** Module 5 covers the formal/informal routes; the EHRC 8-step framework underpins it.
4. **Risk-assessed.** Out of scope of this system — the firm needs a separate documented risk assessment.
5. **Refresher cycle.** Once a year, current data shows. The system supports annual rotation (v1 ships with one bank per module; v2 swaps Year-2 content).
6. **Board oversight.** The signing-officer block on every certificate names the CEO. The compliance review document records that the content has been checked.

When an inquiry lands:
- Pull the CSV.
- Show the COMPLIANCE_REVIEW.md document (it's our internal record that the content has been third-party-checked).
- Show the RESEARCH_SUMMARY.md document (it's our internal record that the system is designed against the latest law and the best available evidence).

## Email cadence + tone

The reminder mailer fires four employee mails per cycle (10/5/2/0 days remaining) and one line-manager mail on day 15 if they're still overdue. Copy is in `scripts/training_reminders.py` (search for `REMINDER_TEMPLATES`).

Tone arc: friendly → tighter → firmer → factual. Never preachy. If you want to change the wording, edit that file directly and commit — there's no separate copy CMS.

## Common questions colleagues will ask

- **"Can I do this on my phone?"** Yes. The page is mobile-first. Tap targets are 44px+, no autoplay, no countdowns.
- **"How long does it take?"** ~70 minutes for the all-staff six. Plus 20 minutes for the Manager add-on if applicable.
- **"What if I get it wrong?"** Three attempts before HR escalation. Each attempt is randomly sampled from the 25-question bank, so the next attempt won't be the same questions.
- **"Will my line manager see my reflections?"** No. The text is in Cloudflare KV, only readable by HR via the admin dashboard.
- **"What happens to this data?"** Retained 7 years by default (configurable in `training-config.json`). Used internally for HR / compliance / tribunal purposes only. Never published.
- **"Why is harassment training a regulatory issue?"** Because under SMCR, a substantiated finding can fail the fitness-and-propriety test. From 1 September 2026, COCON 1.1.7FR makes that explicit across all SMCR firms. (Module 1 §6 + Module 5 §5 cover this.)

## When the system says something HR didn't authorise

The most common scenario: a colleague accuses the system of having auto-enrolled them in something. Tell them:
- Auto-enrolment fires for **new starters** (within 14 days of their start_date in people.json) and for **line managers** (anyone with one or more direct reports recorded on the Directory).
- The dashboard shows the exact reason on each card.
- If they think the enrolment is wrong, exempt them, then have engineering correct the underlying people.json (e.g. an incorrect line_manager_id link).
