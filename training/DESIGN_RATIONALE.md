# TogetherBook Harassment-Prevention Training — Design Rationale & Microcopy Library

**Prepared:** 20 May 2026
**Companion to:** `RESEARCH_SUMMARY.md` §6.3, `research/05_lms_ux_wcag.md`
**Scope:** the visual + verbal spec the engineer builds against. No code; the patterns embedded below are illustrative.

The training is not a separate product. It is a TogetherBook page that happens to be about a serious subject. The job of this document is to make sure it stays that way: same chrome, same palette, same restraint as the rest of `book.togetherbook.net`, but with the typographic and spatial discipline a sensitive subject demands.

---

## 1. Brand fit + design language

### 1.1 It is a TogetherBook page

The page header, nav, hamburger, avatar chip and footer are the standard TogetherBook ones (`.qb-topbar`, `nav.js`, the avatar chip injected by `nav.js`). Drop `quiet-tokens.css`, `quiet.css`, `quiet-extras.css` in the head, exactly as Wall and Holidays do. A colleague landing on `/training.html` from the topbar should feel they have not left the product. The Wall is the closest neighbour visually — single-column, paper card on cream, brass left-rule on the writeable surface, manuscript-red used only for emphasis.

The training is calmer than the Wall (no compose box, no avatars, no reactions) and more text-confident than BookR (long-form prose at a reading width). The single visual signal that this is sensitive content is **space, not chroma**: extra vertical padding around sections, generous line-height, body text wider than the rest of the site (~70ch), and no decoration anywhere on the reading surface.

### 1.2 Typography (no new fonts)

| Use | Family | Notes |
|---|---|---|
| Module + section titles | `var(--font-display)` — Newsreader | Same as `h1`/`h2`/`h3` already in `quiet-tokens.css`. Slightly tighter spacing than the rest of TogetherBook because reading flow matters. |
| Reading body | `var(--font-display)` — Newsreader, 18px / `--lh-loose` (1.75), max-width 70ch | Newsreader is already loaded. Serif reads as "something written for adults to read." This is the one place on TogetherBook where body text is set in the display serif, and it teaches the user "this is reading, not chrome." |
| Quiz questions | `var(--font-display)` — Newsreader, 22px (`--fs-xl`) | The question is content, not chrome. Match the reading body so it feels continuous. |
| Quiz options | `var(--font-body)` — Inter, 16px (`--fs-md`) | The options are interactive controls, not prose. Inter for the same reason buttons are Inter. |
| Buttons, status, stepper, microcopy | `var(--font-body)` — Inter | Already the body font everywhere on TogetherBook. |
| Saved-at timestamp, verification ID | `var(--font-mono)` — JetBrains Mono | Tabular figures matter here. Same monospace as the rest of TogetherBook's metadata. |

### 1.3 Colour (no new tokens)

Everything below is already in `quiet-tokens.css`.

| Use | Token |
|---|---|
| Page background | `var(--bg)` (paper-100, `#FBF6E9`) — same as Wall + Holidays |
| Reading surface card | `var(--bg-raised)` (paper-50, `#FDFBF4`) |
| Body text | `var(--fg)` (ink-800, `#1B2A4E`) — contrast 11:1 on paper, passes AA + AAA |
| Muted text (timestamps, captions) | `var(--fg-muted)` (ink-600, `#4A5878`) — contrast 7.4:1, passes AA + AAA |
| Disabled text | never `--fg-disabled` (ink-300) for live text; reserved for genuinely disabled controls. |
| Primary action (Start, Next, Submit, Complete) | `var(--brass-500)` background, `var(--paper-50)` text — matches the Wall "Post" pill exactly |
| Pressed primary | `var(--brass-600)` |
| Focus ring | `var(--ring-focus)` (3px brass at 45%) plus a 2px solid brass outline (see §5) |
| Correct-answer feedback | `var(--sage-500)` 4px left rule on a `var(--sage-50)` panel. The word "Correct." is `var(--ink-800)`, not green — green is only the rule. |
| Wrong-answer feedback | `var(--red-500)` 4px left rule on a `var(--red-50)` panel. The phrase "That's not the answer." is `var(--ink-800)`. Red is only the rule. |
| Content-warning banner (sexual-harassment sections) | `var(--red-500)` 4px left rule on `var(--red-50)`. Same construction as wrong-answer. |
| Certificate seal + section markers | `var(--brass-500)` |

**Manuscript red discipline.** `var(--red-500)` appears in exactly two places in this product:
1. The 4px left rule on the wrong-answer feedback panel, paired with a 1–2 sentence rationale.
2. The 4px left rule on the content-warning banner that precedes sexual-harassment scenarios.
Never as a fill, never as a chip on its own, never as the word "incorrect." Wrong is always paired with why.

**No new colours. No new fonts. No new iconography that does not already exist on TogetherBook.** If a glyph is needed (the brass certificate seal, the chevron in "Next ›"), it comes from the SVG set already in `wall.html` / `directory.html`. The chevron is a literal `›` character — same as the Wall comment-thread expander.

### 1.4 Surface and chrome

- **No box-shadows on the reading surface.** Paper sits flat on paper. (`--shadow-paper` is reserved for cards that genuinely lift, like the certificate card on the dashboard.)
- **No hover transforms.** Hover changes colour, not position. Same rule as the rest of TogetherBook (see CLAUDE.md §3).
- **Hairline dividers only.** 1px `var(--paper-300)` between sections. No double rules, no inset shadows.
- **Section radius is 0.** Cards on the dashboard use `--radius-md` (10px) to match other dashboard cards. The reading surface itself has no radius — it is a sheet of paper, not a card.

---

## 2. Page architecture

### 2.1 The three URLs and one shared shell

| URL | Mode | Audience |
|---|---|---|
| `/training.html` | Employee dashboard — list of assigned modules with deadline + status, certificate card at the bottom once the cycle is complete | All staff |
| `/training.html?module=<id>` | Module reader + quiz, same page, just a mode switch | All staff |
| `/training-admin.html` | HR-only dashboard — assignment, cohort progress, exemptions, audit-log viewer | HR (Cloudflare Access group) |
| `/training-cert.html?id=<cert_id>` | Single-page certificate view, Cloudflare-Access-gated for the verification flow, public-by-link for the holder | The certificate holder + HR + tribunal verifier |

The shell — topbar, footer, max-width container, mobile drawer — is the same shell every other TogetherBook page renders. Only the `<main>` content varies.

### 2.2 The five phases inside the module reader

Each module moves through five phases. They are URL-addressable via `&phase=cover|read|quiz|reflect|cert` so a `?resume=` link lands the user on the exact phase + step they left.

**Phase 1 — Cover.** Module title, duration estimate ("about 12 minutes"), the one-sentence "what this module is for" line lifted verbatim from the module's first paragraph, and a single primary "Start the module" button. Below the button, in muted text: "You can stop and resume at any point." If the module contains sexual-harassment scenarios, the content-warning banner (§3) appears between the title and the Start button.

**Phase 2 — Reading.** Section navigation as a clickable stepper across the top. One section per screen. Bottom-right primary "Next section ›". Bottom-left text-only "‹ Back". Auto-save on every section transition; the "Saved 14:32" indicator lives in the top-right of the reading surface so it is visible without scrolling.

**Phase 3 — Quiz.** One question per screen. Stepper changes from "Section N/M" to "Question N/M" (same component, different label + count). Bottom bar: text-only "Flag this question" link on the left, primary "Submit answer" on the right. After submission: the in-place feedback panel appears below the options (correct/incorrect + 1–2 sentence rationale), the "Submit answer" button is replaced by a primary "Next question ›". After question 8 of 8: the quiz summary screen.

**Phase 4 — Reflection.** Two open textboxes, each preceded by the prompt + the manager-cannot-see caveat. Autosave indicator per textbox. Below: primary "Complete module".

**Phase 5 — Certificate.** Only shown once the *cycle* (all assigned modules) is complete. Renders the certificate card with the cycle's verification ID + "Download PDF" + "Email me a copy" buttons. Module-by-module completion does not produce a certificate — only the cycle does. This is deliberate: it matches the way HR + the FCA would actually want to reference the record, and stops the certificate from being a per-module trophy.

### 2.3 Wireframes

**Reading (Phase 2):**

```
┌────────────────────────────────────────────────────────────────────┐
│  [ TogetherBook standard topbar ]                                  │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   Module 1 — The Law and Why It Matters         Saved 14:32        │
│   ─────────────────────────────────────────────────────────        │
│   ● 1   ● 2   ○ 3   ○ 4   ○ 5   ○ 6   ○ 7    (clickable stepper)  │
│                                                                    │
│   Section 2 of 7                                                   │
│   The Equality Act 2010 — the foundation                           │
│                                                                    │
│   The Equality Act 2010 protects people from discrimination        │
│   based on nine protected characteristics:                         │
│     · Age                                                          │
│     · Disability                                                   │
│     ...                                                            │
│                                                                    │
│                                                                    │
│   ‹ Back                                       Next section  ›     │
└────────────────────────────────────────────────────────────────────┘
```

**Quiz (Phase 3):**

```
┌────────────────────────────────────────────────────────────────────┐
│  [ topbar ]                                                        │
├────────────────────────────────────────────────────────────────────┤
│   Module 1 — Test                                Saved 14:38       │
│   ●●●●●●○○   Question 6 of 8                                       │
│                                                                    │
│   A senior manager repeatedly compliments a junior colleague       │
│   on her appearance during team meetings. She has not              │
│   complained, but visibly looks uncomfortable. Is this             │
│   potentially harassment?                                          │
│                                                                    │
│   ( ) A.  No, because she hasn't complained.                       │
│   ( ) B.  No, because compliments are not harassment.              │
│   (•) C.  Yes, if a reasonable person would consider the           │
│           conduct has the effect of violating her dignity or       │
│           creating an uncomfortable environment.                   │
│   ( ) D.  Only if he does it again after she objects.              │
│                                                                    │
│   ─────────────────────────────────────────────────────────        │
│   Flag this question                              Submit answer    │
└────────────────────────────────────────────────────────────────────┘
```

After submission (correct shown):

```
│   (•) C.  ...                                                      │
│   ┃                                                                │
│   ┃  Correct.                                                      │
│   ┃  Harassment is judged by purpose or effect, not the            │
│   ┃  recipient's outward reaction — the test is what a             │
│   ┃  reasonable person would conclude.                             │
│                                                                    │
│   Flag this question                              Next question ›  │
```

The `┃` is the 4px `var(--sage-500)` left rule. For a wrong answer the rule is `var(--red-500)` and the panel reads "That's not the answer. Under [statute], [explanation]. The correct answer is C."

**Reflection (Phase 4):**

```
│   Reflection                                     Saved 14:51       │
│   ─────────────────────────────────────────────────────────        │
│                                                                    │
│   1.  In a sentence or two, describe a situation in your team      │
│       where the "purpose or effect" test might apply.              │
│       Your manager will not see this — it's for your own           │
│       reflection.                                                  │
│                                                                    │
│   ┌──────────────────────────────────────────────────────────┐     │
│   │                                                          │     │
│   │                                                          │     │
│   └──────────────────────────────────────────────────────────┘     │
│                                                       Saved 14:51  │
│                                                                    │
│   2.  If you witnessed this in your team next week, what is        │
│       one thing you would do differently because of this           │
│       module? Your manager will not see this.                      │
│                                                                    │
│   ┌──────────────────────────────────────────────────────────┐     │
│   │                                                          │     │
│   └──────────────────────────────────────────────────────────┘     │
│                                                       Saved 14:53  │
│                                                                    │
│                                          Complete module           │
```

**Certificate (Phase 5 + `/training-cert.html`):**

```
┌────────────────────────────────────────────────────────────────────┐
│   TogetherBook                                Richmond Group seal  │
│                                                                    │
│                                                                    │
│                    Certificate of Completion                       │
│                                                                    │
│                                                                    │
│                       Aisha Khan-Bowyer                            │
│                                                                    │
│      has completed the harassment-prevention training cycle        │
│                          for 2026.                                 │
│                                                                    │
│        · Module 0 — Professional conduct in digital channels  v3   │
│        · Module 1 — The law and why it matters                v2   │
│        · Module 2 — Recognising harassment                    v2   │
│        · Module 3 — Bystander action — the 5Ds                v1   │
│        · Module 4 — Power dynamics and high-risk situations   v1   │
│        · Module 5 — Reporting and what happens next           v1   │
│                                                                    │
│                                                                    │
│                       [ CEO signature ]                            │
│                       James Benamor                                │
│                       Group CEO                                    │
│                       Issued on behalf of Richmond Group.          │
│                                                                    │
│                                                                    │
│   ┌──────┐                                                         │
│   │ QR   │   TBK-HRT-2026-0K7M9P             Valid until 20 May    │
│   │ code │   Verify at book.togetherbook.net/training-cert         │
│   └──────┘                                                  2027   │
└────────────────────────────────────────────────────────────────────┘
```

### 2.4 The stepper (the load-bearing UI element)

The stepper is the single most-reused component. It shows real state and every dot is clickable to the steps the user has already passed. Forward dots are visible but not clickable (no forced progression for *reading*; for *quiz* the next question is only clickable once the current question is submitted — non-clickable dots take a `disabled` cursor + `aria-disabled="true"`).

The stepper is the same component in reading and quiz phases — the only difference is the label ("Section 3 of 7" vs "Question 3 of 8") and whether forward steps are click-enabled.

---

## 3. Microcopy library

Each entry below: the **state**, the **copy verbatim**, and a one-line **voice rationale** so the engineer does not drift when tweaking. Anything in `[brackets]` is interpolated server-side from the user / module record.

### Dashboard

**Empty (no assignments).**
> Nothing assigned right now. You'll see modules here when HR enrols you in the next cycle.
*Voice: factual, no apology for an empty state — there is nothing wrong.*

**Assignment row, not yet started.**
> Module 1 — The Law and Why It Matters. About 12 minutes. Due 5 June.
*Voice: title, duration, deadline. Three facts, in that order, no adverbs.*

**Assignment row, in progress.**
> Module 2 — Recognising harassment. Section 3 of 5. About 6 minutes left.
*Voice: same shape as the not-started row; the only difference is a real progress fact replacing "About 12 minutes."*

**Resume card (the priority card at the top of the dashboard when a module is mid-flight).**
> Resume Module 2, section 3 of 5.
*Voice: single sentence, one primary button "Resume". Never "Welcome back."*

**Cycle complete.**
> You've completed the cycle. Your certificate is below.
*Voice: declarative, no exclamation, no congratulations. The certificate does the celebrating.*

**HR-exempted row.**
> HR has marked Module 4 as not required for you. If that's not right, ask HR.
*Voice: never invisible, never patronising; gives the user a route back if it's wrong.*

**Prerequisite-not-met row (manager add-on shown but locked).**
> Complete Module 1 first — you're on section 2 of 5.
*Voice: states the condition + their current state, with a Resume link directly to the prerequisite.*

### Cover page

**Start button.**
> Start the module
*Voice: imperative verb + noun. Same shape as "Post" on the Wall.*

**Sub-line under the Start button.**
> Takes about 12 minutes. You can stop and resume at any point.
*Voice: removes the "what if I get interrupted" anxiety up front.*

**Resume button (instead of Start, when prior progress exists).**
> Resume from section 3
*Voice: tells the user where they're going, not just that they're going somewhere.*

### Reading

**Section save indicator.**
> Saved 14:32
*Voice: muted, mono, no animation, no icon, no "your progress is safe with us." It is a fact, not a feeling.*

**Back link.**
> ‹ Back
*Voice: tertiary control, text only, no border.*

**Next-section primary.**
> Next section ›
*Voice: same shape as the Wall's primary "Post" pill; brass fill.*

**Last section of the module → into the quiz.**
> Start the test
*Voice: shifts register from "reading" to "test"; the user should feel the transition.*

### Content-warning banner (only on sexual-harassment scenarios)

> This section contains scenarios of a sexual nature. If you'd rather pause and speak to someone first, [Employee Assistance Programme] is the route.
*Voice: respects the user's right to opt out without making opting out feel like quitting. The link is a first-class option, not a hyperlink in a paragraph.*

### Quiz

**Submit button.**
> Submit answer
*Voice: verb + noun. Same family as "Start the module" and "Complete module."*

**Right-answer feedback header.**
> Correct.
*Voice: full stop, not exclamation mark. Then the 1–2 sentence elaboration if the question hinges on subtle reasoning. If the question is pure recall ("which of these is *not* a protected characteristic"), the elaboration may be omitted — but the rule is followed for every scenario question.*

**Right-answer elaboration (example for Q3 of Module 1).**
> Correct.
> Harassment is judged by purpose or effect, not the recipient's outward reaction — the test is what a reasonable person would conclude.
*Voice: teaches even when the user got it right. The elaboration is what makes "Explain my answer" do work for retention.*

**Wrong-answer feedback header + body (example for Q3 of Module 1).**
> That's not the answer.
> Under the Equality Act 2010, harassment is judged by its purpose or effect on the recipient, not by whether the person doing it intended offence. The correct answer is C.
*Voice: never "Incorrect." Never "Try again." The rationale references the rule by name + the correct letter.*

**Flag-this-question link.**
> Flag this question
*Voice: text link, no border, sits in the bottom-left of the action bar. Opens a small inline note "Tell us what's wrong with this question," not a modal.*

**Flag-confirmation toast.**
> Thanks — flagged for review.
*Voice: factual; closes the loop without committing to a timeline we can't keep.*

**Next-question primary (after submit).**
> Next question ›
*Voice: same shape as Next section.*

**Quiz summary — passed.**
> You answered 7 of 8 correctly. That's a pass.
*Voice: numbers first, judgement second. No fireworks.*

**Quiz summary — failed, retake available.**
> You answered 5 of 8 correctly. The pass mark is 7. You have two retakes available.
> Take it again
*Voice: tells them the number, tells them the threshold, tells them what's left, gives one primary button. No "don't worry," no "almost there."*

**Quiz summary — failed, retake budget exhausted.**
> You answered 5 of 8 correctly, and have used your three attempts. HR has been notified and will be in touch to schedule a one-to-one.
*Voice: factual + states the actual next step. The "HR has been notified" line is not punitive — it is what the user needs to know to plan their day.*

**Question already flagged this attempt (rare retry condition).**
> You flagged this question. Your answer still counts. We'll review the question separately.
*Voice: clears the user's worry that flagging penalised them.*

### Reflection

**Prompt header (above each textbox).**
> Your manager will not see this — it's for your own reflection.
*Voice: the single most important sentence in the reflection phase. It must appear before the textbox, not inside the placeholder.*

**Textbox placeholder.**
> A sentence or two is plenty.
*Voice: removes the "do I need to write an essay" hesitation.*

**Reflection saved indicator.**
> Saved 14:51
*Voice: identical pattern to the reading-phase indicator. Consistency is the message.*

**Reflection minimum-content check (e.g. user clicks "Complete module" with both boxes empty).**
> Add a sentence in each box before completing. These won't be shared with your manager.
*Voice: re-states the privacy promise at the moment of friction.*

**Complete-module button.**
> Complete module
*Voice: verb + noun. Brass.*

### Module-complete and cycle-complete

**Single module complete (not yet the last in the cycle).**
> Module 1 complete. Module 2 is now available.
*Voice: states the past + the next. No champion language.*

**All modules complete (cycle done).**
> You've completed the cycle. Your certificate is below.
*Voice: identical to the dashboard cycle-complete copy, so the user reads the same words on the page they're on and the dashboard they return to.*

### Certificate

**Header.**
> Certificate of Completion
*Voice: Newsreader 32pt brass. The only place "Completion" carries any weight.*

**Body.**
> [Aisha Khan-Bowyer] has completed the harassment-prevention training cycle for [2026].
*Voice: third-person, dateable, year-stamped. Reads like a chartered-body certificate, not a SaaS badge.*

**Module list line item.**
> Module 1 — The law and why it matters · v2 · completed 20 May 2026
*Voice: title, content version, completion date. The content version is what makes this defensible — a tribunal will want to know which version of the material the colleague actually completed.*

**Signing-officer block.**
> Issued by James Benamor, Group CEO, on behalf of Richmond Group.
*Voice: named individual + role + the firm. Above this line: the CEO's signature image.*

**Verification panel (bottom-left).**
> TBK-HRT-2026-0K7M9P
> Verify at book.togetherbook.net/training-cert
*Voice: scannable verification ID first, URL second. The QR encodes the full URL with `?id=...`.*

**Valid-until panel (bottom-right).**
> Valid until 20 May 2027
*Voice: the next-due date stated as a fact. No "your next cycle starts in N days" countdown.*

**"Download PDF" button (on the on-page certificate).**
> Download PDF
*Voice: verb + noun.*

**"Email me a copy" button.**
> Email me a copy
*Voice: confirms the user gets the email; the sentence is the request and the promise.*

**Email subject (when the user clicks Email me a copy).**
> Your TogetherBook training certificate, 2026 cycle
*Voice: not "Congratulations!" Title + scope + year.*

**Email body, first line.**
> Your certificate for the 2026 harassment-prevention training cycle is attached. The verification link is in the certificate footer if HR or a third party needs to confirm it.
*Voice: tells the holder what it is + how it gets used.*

### Deadline reminders (email)

The voice arc is friendly → tighter → firmer → factual. Never preachy. Same subject-line shape across all four so the inbox view stays predictable: `[TogetherBook training] Module X — N days to go` / `... overdue`.

**10 days remaining.**
> Hi Aisha,
>
> The harassment-prevention training cycle is due on 5 June. You have 10 days, which is plenty — Module 1 takes about 12 minutes.
>
> Open the dashboard: [link]
*Voice: conversational, gives the duration as a reassurance.*

**5 days remaining.**
> Hi Aisha,
>
> Five days to go on the harassment-prevention cycle. If you can find 30 minutes this week the whole thing is done.
>
> Open the dashboard: [link]
*Voice: same warmth, slightly tighter framing — a number a person can plan around.*

**2 days remaining.**
> Hi Aisha,
>
> The harassment-prevention training is due on 5 June — two days away. Please pick up where you left off when you have 30 minutes.
>
> Open the dashboard: [link]
*Voice: firmer (the word "please"), still respectful.*

**Overdue.**
> Hi Aisha,
>
> The deadline for the harassment-prevention training was 5 June. Please complete the remaining modules by 12 June. After that date your line manager and HR are notified automatically.
>
> Open the dashboard: [link]
*Voice: factual. States the original date, the new date, the escalation rule. No moralising. The escalation sentence is part of the same paragraph so it reads as procedure, not threat.*

### HR escalation notice (sent to line manager)

> Hi [manager first name],
>
> [Aisha Khan-Bowyer]'s harassment-prevention training was due on [5 June] and is now overdue. HR has also been copied. A short note from you asking how you can help her find the time often unblocks this.
>
> The dashboard: [link]
*Voice: factual, no judgement of the colleague, gives the manager a constructive action rather than just a status update. The "often unblocks this" sentence is doing real work — it reframes the manager's role from enforcer to enabler.*

### Network / system messages

**Network failure on submit.**
> Couldn't reach the server. Your answer is saved on this device. We'll re-send when you're back online.
*Voice: never just "Error." States what failed, what we did to protect them, what happens next.*

**Stale-tab resume prompt (on focus after 30+ min away).**
> Your progress was saved at 14:32. Pick up here?
*Voice: states the saved state + a single Yes-affirmative button. Never blows away their state.*

**Cloudflare Access re-auth prompt mid-quiz.**
> Your session needs to refresh. Your answer is held — sign back in to continue.
*Voice: explains what's happening, promises the answer is safe.*

**Generic offline banner.**
> Offline. Anything you change will sync when you reconnect.
*Voice: present tense, single sentence, no panic.*

---

## 4. The certificate

A single-page A4 PDF rendered server-side. The Worker generates the HTML; the browser (for the on-page view) and a headless render (for the PDF email) print it. Same source, two transports.

### 4.1 Layout

A4 portrait, 25 mm margins all sides. Three vertical bands.

**Top band (~50 mm tall).**
- Top-left: TogetherBook wordmark, 18pt Newsreader semibold, `var(--fg-strong)`. (The same wordmark already used in `directory.html` headers; do not invent a new one.)
- Top-right: Richmond Group seal at 28 × 28 mm. The seal is a single PNG asset — same one HR uses on offer letters; ask James for the file.

**Centre band (~140 mm tall, centred on the page).**
- "Certificate of Completion" — Newsreader 32pt, `var(--brass-500)`, centred. The only place this phrase appears in the product.
- 18 mm of space.
- The colleague's full name — Newsreader 22pt, `var(--fg-strong)`, centred. Pulled from the SSO display name, never re-typed (WCAG 3.3.7).
- 8 mm of space.
- "has completed the harassment-prevention training cycle for [year]." — 14pt Newsreader regular, centred, `var(--fg-muted)`.
- 10 mm of space.
- Module list, left-aligned within a centred 120 mm-wide block:
  > Module 0 — Professional conduct in digital channels · v3 · 14 May 2026
  >
  > Module 1 — The law and why it matters · v2 · 17 May 2026
  >
  > ...
  > Each row: 11pt Newsreader. The version + date in `var(--fg-muted)` JetBrains Mono. Version is the load-bearing audit fact — a tribunal will want to know exactly which content was completed.
- 18 mm of space.
- Signature block, centred:
  - CEO signature image (PNG, ~50 mm wide, transparent background, James to provide)
  - Below: "James Benamor" — 12pt Newsreader semibold, `var(--fg-strong)`
  - Below: "Group CEO" — 10pt Inter, `var(--fg-muted)`
  - Below: "Issued on behalf of Richmond Group." — 10pt Inter italic, `var(--fg-muted)`

**Bottom band (~30 mm tall).**
- Bottom-left:
  - QR code, 22 × 22 mm, black on white, encoding the full URL `https://book.togetherbook.net/training-cert.html?id=<verification_id>`
  - To the right of the QR: the verification ID `TBK-HRT-2026-0K7M9P` in 11pt JetBrains Mono on one line; under it "Verify at book.togetherbook.net/training-cert" in 9pt Inter, `var(--fg-muted)`.
- Bottom-right:
  - "Valid until 20 May 2027" — 11pt Inter semibold, right-aligned, `var(--fg-strong)`.

### 4.2 Verification ID format

`TBK-HRT-<year>-<6 base32-Crockford chars>`. Base32-Crockford because it survives being read out over the phone (no I/1, no O/0). 6 chars over 32^6 = ~1 billion ids — comfortably collision-free at the firm's scale. Stored server-side keyed to the certificate record.

### 4.3 The `/training-cert.html?id=...` verification page

Renders the same certificate, with one addition: a small panel above the certificate, on `var(--paper-50)` with a `var(--brass-500)` left rule, that reads:

> This certificate was issued by Richmond Group on 17 May 2026 to Aisha Khan-Bowyer and is valid until 20 May 2027. It covers the modules listed below.

Below the certificate, a second panel for tribunal-defensibility:

> Audit record
> Issued 17 May 2026 · Issued by TogetherBook · Cycle 2026 · Verification ID TBK-HRT-2026-0K7M9P · Content version snapshot stored.

This panel exists so a tribunal verifier or HR officer at another firm can land on this URL and see the chain of custody in plain English. It does not appear on the printable PDF — only on the on-page verification view.

### 4.4 Design discipline

- No avatar carousel.
- No badge graphic.
- No rainbow gradient anywhere.
- No "Powered by TogetherBook" footer.
- No social-share buttons.
- The only colours on the page are `var(--brass-500)`, `var(--fg-strong)`, `var(--fg-muted)`, paper background. That's it.

The benchmark: a certificate from a chartered body. The user should feel it is appropriate to print and put in a portfolio. If the choice you are about to make would feel out of place on a chartered-accountant's wall, do not make it.

---

## 5. WCAG 2.2 AA — implementation checklist

Flat checklist. Tick through. Rationale for each is in `research/05_lms_ux_wcag.md`.

- [ ] **1.4.3 Contrast.** Body text uses `var(--fg)` (ink-800) — measured 11:1 on `var(--bg)`. Muted text uses `var(--fg-muted)` (ink-600) — measured 7.4:1. Never use `var(--ink-500)` or lighter for live body text.
- [ ] **1.4.11 Non-text Contrast.** Radio + checkbox borders use `var(--border-strong)` (ink-300) — measured 3.1:1. The stepper's unfilled-dot ring uses `var(--border-strong)`. Buttons in their resting state have a 1px `var(--brass-500)` outline or a `var(--brass-500)` fill — both pass.
- [ ] **2.2.1 Timing Adjustable.** No per-question timer anywhere. No session timeout other than the Cloudflare Access default, which is well past the WCAG threshold for adjustability.
- [ ] **2.3.3 Animation from Interactions.** Every transition in the training UI is gated by `@media (prefers-reduced-motion: no-preference)`. `quiet-tokens.css` already has the kill-switch at the bottom — verify any new keyframes inherit the same gate. No autoplay video.
- [ ] **2.4.6 Headings and Labels.** Module title is `<h1>`. Section title is `<h2>`. Each quiz question is `<h2>` (one question per screen, so each screen has exactly one H2). Reflection textboxes use `<label for>`, not placeholder-only. The stepper uses descriptive button text ("Go to section 3 — What harassment legally means"), surfaced to screen readers via `aria-label`, while sighted users see the dot + numeric label.
- [ ] **2.4.7 Focus Visible.** Every interactive control gets `outline: 2px solid var(--brass-500); outline-offset: 3px` on `:focus-visible`. Never `outline: none` without an equivalent replacement.
- [ ] **2.4.11 Focus Not Obscured (Minimum) — new in 2.2.** `html { scroll-padding-top: 80px; }` already exists in `quiet-tokens.css` for the sticky topbar. Verify it remains in force on the training page; if the quiz adds its own sticky footer, extend `scroll-padding-bottom` to match its height.
- [ ] **2.4.13 Focus Appearance (AAA stretch).** The 2px brass outline at 3px offset passes both 2px-perimeter and 3:1 contrast requirements against both `var(--paper-50)` (surface) and `var(--paper-100)` (page background).
- [ ] **2.5.7 Dragging Movements — new in 2.2.** No question type uses drag-and-drop. If a "match the term to the definition" question is introduced later, it must also support tap-to-select-then-tap-to-place.
- [ ] **2.5.8 Target Size (Minimum) — new in 2.2.** All radio options, the Submit / Next / Back buttons, and the "Flag this question" link have a minimum 44px tap height on mobile. The footer action bar maintains ≥ 8px gap between Back, Flag, and Submit.
- [ ] **3.1.3 Unusual Words (AAA — worth meeting).** Legal terms — "protected characteristic", "victimisation", "vicarious liability", "SMCR", "F&P", "COCON" — are wrapped in `<dfn>` with a hover/tap glossary popover. The Glossary page lives at `/training.html#glossary` and is linked from the persistent training nav.
- [ ] **3.3.1 / 3.3.3 Error Identification + Suggestion.** Wrong-answer feedback always: states it is wrong; names the rule; names the correct answer letter. Never bare "Incorrect." See §3 microcopy.
- [ ] **3.3.7 Redundant Entry — new in 2.2.** Certificate name + email pulled from SSO, never re-typed. If a user retakes a module, prior reflection-textbox answers pre-fill (editable). The flag-question form does not re-ask the question text — it shows it.
- [ ] **3.3.8 Accessible Authentication (Minimum) — new in 2.2.** Resume relies on the existing Cloudflare Access session. No captcha, no security questions, no "type the word from the image." Password managers must be able to paste into any input on `/training-cert.html` (the only auth-adjacent page).
- [ ] **4.1.3 Status Messages.** The "Saved 14:32" indicator, the correct/wrong feedback panel, the "Section complete" toast, the "Couldn't reach the server" toast all use `role="status"` (polite) or `aria-live="polite"`. The retake-exhausted message uses `role="alert"` because it is a state change the user must hear. None of these steal focus.

```html
<!-- Saved indicator pattern -->
<span class="tr-saved" role="status" aria-live="polite">Saved 14:32</span>

<!-- Wrong-answer feedback pattern -->
<aside class="tr-feedback tr-feedback--wrong" role="status" aria-live="polite">
  <p class="tr-feedback-head">That's not the answer.</p>
  <p class="tr-feedback-body">Under the Equality Act 2010, ... The correct answer is C.</p>
</aside>
```

---

## 6. Mobile patterns

The training has to feel native on a 375px-wide iPhone SE because half of staff will start it on the bus.

- **One question per screen on mobile, always.** Desktop may eventually support a review-list view; mobile never does.
- **Tap targets ≥ 44px tall.** Option buttons, Submit, Next, Back, Flag — all enforce min-height: 44px and ≥ 8px gap between adjacent footer controls.
- **Sticky bottom action bar.** Submit / Next / Flag / Back live in a sticky bar at the bottom of the viewport on mobile so the user never thumb-stretches. The bar is `var(--bg-raised)` with a 1px top border of `var(--paper-300)`. Honour `scroll-padding-bottom` equal to the bar height so a focused option is never obscured (WCAG 2.4.11).
- **Stepper collapses on narrow viewports.** Below 600px the dot row becomes `Section 3 / 7` text with a `‹` and `›` to jump between, plus a small "Sections" link that opens a sheet listing all sections with their titles + completion ticks.
- **Scroll restoration on answer.** After Submit, scroll the viewport so the feedback panel's top sits 16px under the stepper. Do not jump to the top; do not leave the user staring at the option they picked with the feedback off-screen.
- **No fixed-height scroll containers.** Let the page scroll natively; do not wrap the reading body in a scrollable div. Mobile scroll restoration breaks otherwise.
- **No autoplay video.** Any video has an explicit play control and a transcript link directly under the player.
- **Reading body width on mobile.** The 70ch ceiling is desktop-only. On mobile the reading body fills the viewport with 16px gutters — the line length naturally falls into the readable range at that width.
- **Certificate on mobile.** The on-page certificate view renders at its native A4 ratio inside a horizontally-scrollable card with `min-width: 600px`. The mobile user reads the summary panel above it (issued to / valid until / verification ID) at full width, and downloads the PDF for the actual document. Do not reflow the certificate itself to mobile — it is a document, not a webpage.

---

## 7. Failure and edge-case UI

**Network failure on submit (quiz or reflection).**
A toast — `role="status"`, polite — appears at the top of the viewport:
> Couldn't reach the server. Your answer is saved on this device. We'll re-send when you're back online.

The answer (or reflection text) is written to `localStorage` keyed by `module_id + question_id + user_id`, with a 7-day TTL. On regaining connectivity (`window.online` event), the queue is flushed. If the server confirms receipt the local copy is cleared; if it 4xx/5xxs, the toast re-appears with a "Retry" inline link.

**Stale tab (user returns after 30+ min away).**
On the `focus` event after 30 minutes of inactivity, surface a non-blocking banner at the top of the reading / quiz surface:
> Your progress was saved at 14:32. Pick up here?

with a single "Continue" primary button. The page state is *never* wiped. The banner is dismissable. If the user has actually advanced in another tab in the meantime, the banner reads:
> You've moved further along in another tab. Continue there, or [refresh this one] to catch up.

**Manager add-on shown but prerequisite not met.**
Inline on the dashboard row, not a modal:
> Complete Module 1 first — you're on section 2 of 5.

with a "Resume Module 1" link that deep-links into the exact section. The Manager add-on row stays visible (not hidden) so the user understands what's queued.

**HR exemption.**
The exempted module renders on the dashboard as a row with a 4px `var(--brass-500)` left rule and the text:
> HR has marked Module 4 as not required for you. If that's not right, ask HR.

with a "Message HR" link that opens a mailto to the configured HR address with a pre-filled subject "Training exemption query — Module 4." Never hide an exempted module — the user has to be able to challenge it.

**Cloudflare Access timeout mid-quiz.**
The Cloudflare Access redirect intercepts the next request. When the user signs back in, they return to the same URL (Access preserves the original request). The quiz state is in `localStorage` (per the network-failure pattern above), so the answer they were about to submit is held. A toast on return:
> Welcome back. Your answer was held — Submit when you're ready.

**Reflection textboxes lost focus before autosave fired.**
Reflection autosave fires on `blur` and on a 5-second debounced interval while typing. On `beforeunload` if there is unsaved text in either box, a native confirmation prompt fires:
> You have unsaved reflections. Stay on this page to save them.

This is the one place we use the browser-native prompt because it is the only intervention strong enough to stop accidental tab-close.

**Server says the user has already completed the module they're currently in.**
(Race condition: same colleague opened two tabs and completed in one.) The current tab shows:
> Looks like you've already completed this module in another tab — well played for being thorough. We've kept the higher score.

with a "Back to dashboard" primary button. This is the one piece of microcopy in the product allowed a small piece of warmth, because the user has just done extra work and we owe them an acknowledgement.

**Admin (HR) action: bulk-assign cycle to 200 colleagues, partial failure.**
The admin sees a summary panel:
> Assigned 198 of 200. Two colleagues were skipped — they're not in the active directory: aisha.former@richmondgroup.co.uk, james.left@richmondgroup.co.uk. Remove them from the cohort and try again.

Never "Some assignments failed. See logs." Always say who, why, what to do.

---

## Acceptance criteria — recap

- Existing TogetherBook palette + typography honoured. No new design tokens introduced. Every colour and font cited above is already in `quiet-tokens.css`.
- Microcopy library covers every state the engineer will build, verbatim, with a voice-rationale comment per state.
- Certificate spec is concrete enough to build from a single read — layout band-by-band, exact tokens, exact phrasing, verification-ID format, the verification-page extension.
- WCAG checklist is actionable, mapped to specific tokens and patterns, with the four new-in-2.2 criteria called out.
- The training page reads as a TogetherBook page that has been quieted down for a serious subject — not as a separate product wearing the TogetherBook header.
