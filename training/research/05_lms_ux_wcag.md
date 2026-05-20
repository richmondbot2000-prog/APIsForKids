# Corporate-Training UX & WCAG 2.2 AA — Research Summary for TogetherBook

## Part A — Corporate-training UX done well

### 1. Duolingo / Khan Academy — what survives translation to one-off compliance

The genuinely portable lessons from gamified mobile learning are not the streaks or the cartoon owl — they are the **micro-feedback loop** and the **safety of being wrong**.

- **"Explain my answer" is the load-bearing pattern.** When a learner gets a question wrong, Duolingo doesn't just say "Incorrect" — it explains the rule the user tripped on and tailors the explanation to the specific error made. Translated for a compliance module: every wrong answer surfaces a 1-2 sentence "this is the right answer, because…" panel inline below the question, not a modal ([edtechinnovationhub.com](https://www.edtechinnovationhub.com/news/duolingo-to-offer-all-users-ai-powered-feedback-tool-explain-my-answer-starting-in-the-new-year)).
- **Wrong answers trigger gentle visuals, not red error screens.** Users need to feel safe being wrong; the visual design reinforces that ([blakecrosley.com](https://blakecrosley.com/guides/design/duolingo)). For TogetherBook this means an amber underline + a calm explanatory note, never a slammed red banner with an X icon.
- **Immediate state change after every action.** A pulse / fill of the progress bar on every correct answer is the cause-and-effect signal — not a delayed reveal at the end of the section ([medium.com — micro-interactions](https://medium.com/@Bundu/little-touches-big-impact-the-micro-interactions-on-duolingo-d8377876f682)).
- **What does NOT translate**: streaks, hearts/lives, mascots, leaderboards. A one-off compliance module is not a daily habit product, and applying retention mechanics to it reads as patronising.

### 2. Notion onboarding — text-heavy yet feels light

Notion's onboarding is the closest mass-market parallel to "a serious thing taught well."

- **Learn-by-doing checklist on the user's own page** — the tour is a working document, not a series of overlay coach-marks ([goodux.appcues.com](https://goodux.appcues.com/blog/notions-lightweight-onboarding)).
- **Progressive disclosure**: features appear when relevant, not upfront ([candu.ai](https://www.candu.ai/blog/how-notion-crafts-a-personalized-onboarding-experience-6-lessons-to-guide-new-users)).
- **High-contrast tooltips appear on hover** — instruction is available but never imposed.
- **No forced linear path**: users explore based on preference; lock-step navigation signals distrust ([coursy.io on why employees hate compliance training](https://coursy.io/blog/2026/03/24/why-employees-hate-compliance-training-and-what-actually-works-instead/)).

### 3. Linear & Stripe — the "respect for intelligence" aesthetic

- **Heavy use of Inter (or similar) sans, dark grey on near-black or near-white**, not pure black on white. Linear's brand colour is a deliberately desaturated blue used sparingly ([linear.app/brand](https://linear.app/brand), [linear.app/now/how-we-redesigned-the-linear-ui](https://linear.app/now/how-we-redesigned-the-linear-ui)).
- **Restrained colour is a credibility signal**: monochrome reads as "for adults"; bright multicolour reads as "for end-users who need persuading." The Linear redesign explicitly reduced colour to "increase hierarchy and density of navigation elements" ([logrocket](https://blog.logrocket.com/ux-design/linear-design/)).
- **Premium UI = visible decisions**: hairlines, focus rings, tabular figures, hover states, empty states all designed rather than defaulted ([mantlr.com](https://mantlr.com/blog/stripe-linear-vercel-premium-ui)).
- **Stripe's typographic-chromatic foundation**: Söhne (or similar neutral grotesque), tabular numerals in financial tables, indigo used only as accent. The craft is in *what isn't flashy*.

### 4. GitHub Actions / wizard flows — progress as legible state

- **Workflow runs show state, not theatre**: which step is running, which finished, which is queued — each line independently inspectable ([github.blog/changelog](https://github.blog/changelog/2024-04-30-github-actions-ui-improvements/)).
- For a quiz, this means: a stepper showing "Section 2 of 5 · 3 of 8 questions answered" with each section openly clickable, not a single throbbing percentage bar.
- **No theatrical loaders** — if a state change is instant, render it instantly; loaders should only appear when there is genuine network latency over ~400ms.

### 5. FutureLearn / Open University — the closest "structured reading + quiz" parallel

- **Lesson ends with a 5-question multiple-choice quiz**; module ends with a longer task ([futurelearn — User Experience Basics](https://www.futurelearn.com/courses/digital-skills-user-experience/17)). The 5-question-per-section cadence is well-established and survives translation.
- Free-mixing **video, article, quiz, discussion** within a module ([futurelearn — UX Design course](https://www.futurelearn.com/courses/user-experience-design)) — but for an internal compliance build the discussion thread is generally a liability (HR/legal review burden); reflection textboxes are the safer equivalent.

### 6. Apple Health / NHS App — regulated, sensitive content done calmly

- **Calm UX reduces drop-off when users are stressed** — clean hierarchy, one decision at a time, no urgency theatre ([diversido.io](https://www.diversido.io/blog/how-does-ux-ui-impact-your-wellness-app)).
- **Ada Health** specifically presents medical assessment as a "calm, one-question-at-a-time chat flow" — exactly the pattern a sensitive D&I module needs ([imaginarycloud](https://www.imaginarycloud.com/blog/3-healthcare-apps-with-the-best-ui-ux-design)).
- Regulated content design principle: **safety, traceability, and clarity over speed**.

### 7. Stripe Docs / Vercel Docs / Tailwind UI — typography & spacing benchmark

- **Three-column layout**: nav · content · in-context aside (code/example/glossary) ([moesif](https://www.moesif.com/blog/best-practices/api-product-management/the-stripe-developer-experience-and-docs-teardown/)).
- **Body text ~16-18px, line-height 1.6-1.75, max line length ~70ch** is the de facto reading benchmark.
- **Big low-contrast headlines, generous spacing** ([vercel/geist/typography](https://vercel.com/geist/typography)).
- Docs feel like an *application*, not a manual ([mintlify on Stripe docs](https://www.mintlify.com/blog/stripe-docs)) — implication: the training module should feel like a working tool, not a slide deck.

### Concrete patterns to extract

| Pattern | Implementation |
|---|---|
| **Progress as state, not animation** | Stepper showing "Section 2/5 · Q 3/8" with each step nav-able; never a throbbing percentage |
| **Save-and-resume** | Visible "Saved 14:32" timestamp + on return, a card "Resume where you left off: Section 2, Q4" — not "Continue" with no context |
| **Question UI** | Mobile: one question per screen, full-width tap targets. Desktop: optional list view for review. After answer: inline 1-2 sentence explanation for *both* right and wrong picks. A small "Flag this question" link |
| **Reflection prompts** | Open textbox, autosave indicator ("Saved 2s ago"), explicit "Your manager will not see this" caveat above the box |
| **Certificate** | Single-page PDF: name, date, module(s), signing officer, unique verification ID. Designed like a document an employee would put in a portfolio ([certifier.io](https://certifier.io/blog/completion-certificate-templates)), not a glossy "Woohoo!" avatar carousel |
| **Mobile** | Tap targets ≥ 44px tall, no fixed-height scroll containers, no autoplay video, scroll position restored after answer feedback renders |

---

## Part B — WCAG 2.2 AA: the 15 criteria that matter for this build

Build implication in italics. Sources: [w3.org/WAI/standards-guidelines/wcag/new-in-22/](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/), [w3.org/TR/WCAG22/](https://www.w3.org/TR/WCAG22/).

1. **1.4.3 Contrast (Minimum) — AA.** Text ≥ 4.5:1; large text (≥ 24px or ≥ 18.5px bold) ≥ 3:1 ([testparty](https://testparty.ai/blog/color-contrast-requirements)). *Implication: the calm grey-on-grey Linear aesthetic must be measured; `#71717a` on white fails — go no lighter than `#52525b` for body text.*

2. **1.4.11 Non-text Contrast — AA.** UI components and meaningful graphics ≥ 3:1 vs adjacent colour ([w3.org](https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast.html)). *Implication: the unselected radio/checkbox border, the unfocused button outline, progress-bar track all need ≥ 3:1 against the page background. A `#e5e7eb` border on white fails — use `#a1a1aa` or darker.*

3. **2.2.1 Timing Adjustable — A.** No countdown on quizzes unless adjustable, extendable, or essential ([w3.org](https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html)). *Implication: no per-question timers. If the module has an overall session timeout, warn at -20s with a one-click extend.*

4. **2.3.3 Animation from Interactions — AAA (still worth honouring).** `prefers-reduced-motion` must disable non-essential motion ([w3.org technique C39](https://www.w3.org/WAI/WCAG22/Techniques/css/C39)). *Implication: wrap every transition/animation in `@media (prefers-reduced-motion: no-preference)`; the correct-answer pulse, the section-complete checkmark fade, the page transitions all need a static fallback.*

5. **2.4.6 Headings and Labels — AA.** Every section labelled meaningfully; every form field labelled. *Implication: each quiz question is an `<h2>` or `<h3>`, the reflection textbox has a `<label for>` (not placeholder-only), and the section nav uses descriptive text not "Section 1, Section 2".*

6. **2.4.7 Focus Visible — AA.** Every interactive element shows a focus ring. *Implication: never set `outline: none` without an equivalent replacement; the focus ring needs to survive into the chosen Linear/Stripe aesthetic — a 2px solid ring with ~3px offset in the brand accent is the safe default.*

7. **2.4.11 Focus Not Obscured (Minimum) — AA (new in 2.2).** Focused element not entirely hidden by author content ([w3.org](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html)). *Implication: any sticky header/footer/cookie-banner must `scroll-padding` on the scroll container so a focused question is never tucked under it.*

8. **2.4.13 Focus Appearance — AAA (worth meeting as a stretch).** Focus ring area ≥ 2px-thick perimeter, 3:1 contrast between focused/unfocused states ([allaccessible](https://www.allaccessible.org/blog/wcag-2413-focus-appearance-guide)). *Implication: 2px outline minimum; design choosing a brand accent that is 3:1 from both the button fill and the page background.*

9. **2.5.7 Dragging Movements — AA (new in 2.2).** Every drag has a single-pointer alternative ([w3.org](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html)). *Implication: if a "match the term to the definition" question uses drag-and-drop, also provide tap-to-select-then-tap-to-place. Cleaner: avoid drag-based question types entirely.*

10. **2.5.8 Target Size (Minimum) — AA (new in 2.2).** Touch targets ≥ 24×24 CSS px, or spaced so a 24px circle around each doesn't intersect another target ([w3.org](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)). *Implication: question option buttons should be ≥ 44px tall on mobile (Apple HIG / WCAG comfort target); the "Flag question" + "Next" + "Back" controls in the footer need ≥ 8px margins between them.*

11. **3.1.3 Unusual Words — AAA (worth meeting given UK FS legal vocabulary).** Glossary mechanism for jargon ([w3.org](https://www.w3.org/WAI/WCAG21/Understanding/unusual-words.html)). *Implication: legal terms (e.g. "protected characteristic", "victimisation", "vicarious liability") are wrapped in a `<dfn>` with a hover/tap glossary popover, and a single Glossary page is linked from the persistent nav.*

12. **3.3.1 Error Identification / 3.3.3 Error Suggestion — A / AA.** Errors must say *what* and *why*, and suggest a fix. *Implication: wrong-answer feedback reads "That's not quite it. The correct answer is X. The Act requires Y in this case." — never just "Incorrect."*

13. **3.3.7 Redundant Entry — A (new in 2.2).** Don't re-ask for info already provided in the same process ([w3.org](https://www.w3.org/WAI/WCAG22/Understanding/redundant-entry.html)). *Implication: name/email on the certificate is pulled from the SSO session, never re-typed; if the user re-takes a module, prior reflection-textbox answers pre-fill (editable).*

14. **3.3.8 Accessible Authentication (Minimum) — AA (new in 2.2).** No cognitive-function tests for resume ([w3.org](https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum.html)). *Implication: returning to resume must rely on the existing Cloudflare Access / SSO session — no captcha, no "type the word from the image", no security questions. Password managers must be able to paste.*

15. **4.1.3 Status Messages — AA.** Quiz feedback announced to screen readers without focus shift ([w3.org](https://www.w3.org/WAI/WCAG21/Understanding/status-messages.html), [testparty](https://testparty.ai/blog/wcag-4-1-3-status-messages-2025-guide)). *Implication: the "Saved 14:32" indicator, the correct/wrong feedback panel, and the "Section complete" toast use `role="status"` (polite) or `role="alert"` (assertive) — never steal focus from the question button the user just pressed.*

---

## Part C — Tone & UX writing

How "intelligent-adult tone" gets executed in microcopy. The bar: copy a thoughtful colleague would send. The infantilising tone of typical compliance training actively damages retention — when the material is pitched at primary-school level, the brain learns to trivialise the subject ([coursy.io](https://coursy.io/blog/2026/03/24/why-employees-hate-compliance-training-and-what-actually-works-instead/)).

**Empty state**
- Bad: *"Oh no, looks like you have unfinished business! Let's get you back on track, champion!"*
- Good: *"Module 3 — Equality Act — not yet started. About 12 minutes."*

**Saved indicator**
- Bad: *"All your progress is safe with us!"* (animated cloud icon)
- Good: *"Saved 14:32"* in muted text, no animation.

**Resume**
- Bad: *"Welcome back! Ready to continue your journey?"*
- Good: *"Resume Module 2, Question 4 of 8."* (single primary button)

**Wrong answer**
- Bad: *"Incorrect! Try again!"* (red, with X icon)
- Good: *"That's not the answer. Under the Equality Act 2010, indirect discrimination is when a policy applies equally to everyone but disadvantages a protected group. The correct answer is B."* ([best practice on humanising errors — Smashing Magazine](https://www.smashingmagazine.com/2024/06/how-improve-microcopy-ux-writing-tips-non-ux-writers/))

**Right answer**
- Bad: *"Awesome! You're a superstar!"*
- Good: *"Correct."* — then optionally a 1-line elaboration if the question hinges on subtle reasoning.

**Section complete**
- Bad: *"Woohoo, great job!"* + confetti
- Good: *"Module 1 complete. Module 2 is now available."*

**Reflection prompt**
- Bad: *"Tell us your innermost thoughts!"*
- Good: *"In a sentence or two, describe a situation in your team where this might apply. Your manager will not see this — it's for your own reflection."* + autosave indicator.

**Completion**
- Bad: *"YOU DID IT! You're now a certified D&I champion!"*
- Good: *"You have completed the Diversity & Inclusion module on 20 May 2026. Your certificate is below."*

---

## Design implications for TogetherBook

WCAG-driven (one per criterion needing special handling):

1. **Body text must be ≥ 4.5:1 against background** — `#52525b` minimum on white for normal text (1.4.3).
2. **Unfocused borders on radios/checkboxes/buttons need ≥ 3:1 vs background** — `#a1a1aa` or darker (1.4.11).
3. **No per-question countdown timers**; if session-level timeout exists, warn at -20s with one-click extend (2.2.1).
4. **Wrap all transitions in `@media (prefers-reduced-motion: no-preference)`** — the correct-answer pulse, section-complete check, page transitions all have static fallbacks (2.3.3).
5. **Each question is a real `<h2>`/`<h3>` heading**; reflection textbox uses `<label for>`, not placeholder-only (2.4.6).
6. **2px solid focus ring with 3px offset** in the brand accent on every interactive control; never `outline: none` (2.4.7, 2.4.13).
7. **`scroll-padding-top` on the scroll container** equal to sticky-header height so a focused question is never obscured (2.4.11).
8. **No drag-based question types** — or if used, also support tap-to-select-then-tap-to-place (2.5.7).
9. **Question option buttons ≥ 44px tall on mobile**, ≥ 8px gap between adjacent footer controls (2.5.8).
10. **Legal terms wrapped in `<dfn>` with tap/hover popover**; persistent link to a single Glossary page (3.1.3).
11. **Wrong-answer feedback explains *why*, not just "Incorrect"** — reference the rule, statute, or principle (3.3.1, 3.3.3).
12. **Name/email pre-populated from SSO**; prior reflection answers persist on re-take (3.3.7).
13. **Resume relies on existing Cloudflare Access session** — no captcha, no security questions, no memorisation (3.3.8).
14. **All feedback toasts use `role="status"` or `aria-live="polite"`** — never steal focus from the just-pressed button (4.1.3).

UX-pattern bullets:

15. **Progress is a clickable stepper showing real state** — "Section 2/5 · Q 3/8" — never a single throbbing percentage bar.
16. **One question per screen on mobile; optional list/review view on desktop**; smooth scroll restoration after the feedback panel renders.
17. **Visible "Saved 14:32" timestamp** + on return, a card "Resume Module 2, Q4 of 8" with a single primary button.
18. **Inline 1-2 sentence explanation after *every* answer** (right and wrong); small "Flag this question" link under each.
19. **Reflection textboxes carry an explicit "Your manager will not see this" caveat** + autosave indicator.
20. **Certificate is a single-page PDF**: full name (from SSO), date, module(s), signing officer, verification ID. No avatar carousel, no confetti.
21. **Restrained colour palette** — one brand accent used as accent, not chrome; Inter or similar neutral grotesque; tabular numerals in any scored/quantitative display.
22. **No autoplay video, no audio without explicit play**; transcripts available for any video.
23. **Microcopy reads like a thoughtful colleague** — "Correct.", "That's not the answer. The Act says…", "Module 1 complete. Module 2 is available." — never "Woohoo champion!"

---

**Sources:**
- [W3C — What's new in WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/)
- [W3C — WCAG 2.2 spec](https://www.w3.org/TR/WCAG22/)
- [Duolingo — Explain My Answer (EdTech Innovation Hub)](https://www.edtechinnovationhub.com/news/duolingo-to-offer-all-users-ai-powered-feedback-tool-explain-my-answer-starting-in-the-new-year)
- [Linear — Brand guidelines](https://linear.app/brand)
- [Linear — How we redesigned the UI](https://linear.app/now/how-we-redesigned-the-linear-ui)
- [Mantlr — How Stripe, Linear, Vercel ship premium UI](https://mantlr.com/blog/stripe-linear-vercel-premium-ui)
- [Moesif — Stripe developer experience teardown](https://www.moesif.com/blog/best-practices/api-product-management/the-stripe-developer-experience-and-docs-teardown/)
- [Coursy — Why employees hate compliance training](https://coursy.io/blog/2026/03/24/why-employees-hate-compliance-training-and-what-actually-works-instead/)
- [Smashing Magazine — UX writing tips for non-UX writers](https://www.smashingmagazine.com/2024/06/how-improve-microcopy-ux-writing-tips-non-ux-writers/)
- [Certifier — Course completion certificate templates](https://certifier.io/blog/completion-certificate-templates)
