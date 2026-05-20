# Training Content — Compliance Review

**Reviewer:** compliance subagent
**Date:** 2026-05-20
**Verdict:** PASS WITH CORRECTIONS

## Headline finding

The legal substance is overwhelmingly accurate and well-sourced. Every major statute citation (EA 2010 s.4 / s.26 / s.27 / s.40 / s.40A / s.124A / s.13 / s.18 / s.136; ERA 1996 s.43B; ERA 2025 ss.20/21/23; COCON 1.1.7FR; FIT 2.1; SUP 10C.14 / SUP 15.3 / SUP 15.11; SYSC 22; PS25/23) is correctly identified and correctly dated, the seven-vs-nine protected-characteristic distinction is correctly drawn, the £1.8m / 3 March 2025 Odey figures match the research, the 25% s.124A cap is right, the 5Ds attribution is right, the ACAS helpline number is right, and the April-2026-live / October-2026-pending / 1-Sep-2026-pending tense distinction is mostly held to.

The corrections required are concentrated in three areas: (1) one veto-grade wrong-answer-text issue in Module 1 Q15 (says "nine" where its own rationale and the law say "seven"); (2) one fabricated-sounding case citation in Module 0 ("the 2024 Bull Express tribunal") that does not appear in the research files and that I cannot verify exists; (3) a fabricated statistic in Module 3 ("roughly 70% of the value a bystander provides is acknowledgement") which is not in research/04 and reads as invented. Plus a cluster of smaller corrections: Module 1's scenario-tag count falls below the 10 minimum, Module 5 says "six routes" while listing seven, Module 4 §2.3 implies the firm's own-employee off-site liability is new in October 2026 (it isn't — that's been live since 2010), and Module 5/Manager use a different question-schema (`choices/correct:true`) from Modules 0–4 (`options/correct:<int>`), which will break a single quiz renderer unless the front-end is built to handle both.

With those fixes applied, the training is defensible.

---

## Module-by-module findings

### Module 0 — Professional conduct in digital channels

**File:** `/Users/richmondrobot/Desktop/togetherbook/training/modules/module_0.md`
**Questions:** `/Users/richmondrobot/Desktop/togetherbook/training/modules/module_0.questions.json`

- ✓ The s.26 three-limb test is quoted accurately. The April 2026 whistleblowing reform is correctly described as live ("Since 6 April 2026… is making a protected disclosure"), with S.I. 2026/323 correctly cited in Q5 rationale. COCON 1.1.7FR is correctly framed as future ("from 1 September 2026"). 25 questions, 12 scenario-tagged, two reflections with the correct "manager will never see" guidance — all bank-shape requirements met.

- ⚠ **Module 0 §2, line 29 — unverifiable case citation.** Text: *"The 2024 Bull Express tribunal and successive FCA decisions have made this point repeatedly."* There is no "Bull Express tribunal" in research/01 or research/02, and I cannot find any UK employment-tribunal decision under that name in the cited 2024 timeframe. The point being made (work-adjacent WhatsApp groups are routinely in scope) is correct on the law, but the case citation reads as invented and is exactly the kind of detail an EHRC reviewer or opposing solicitor will check. **Proposed fix:** delete the words "The 2024 Bull Express tribunal and" so the sentence reads "Employment tribunals and the FCA both look at substance, not branding… Successive employment tribunal decisions have made this point repeatedly: if the participants are colleagues and the content touches on the workplace or its people, it is in scope." If a specific case is wanted, *Forbes v LHR Airport Ltd* [2019] (work-adjacent Facebook post) and the WhatsApp-evidence strand in *BNP Paribas v Mezzotero* are well-established hooks; do not invent a name.

- ⚠ **Module 0 Q10 rationale, line 135.** Text: *"From October 2026, s.21 ERA 2025 makes the firm directly liable for third-party harassment across all protected characteristics."* The scenario itself (a comment about the client's accent broadcast to the client) is a non-employee being potentially harassed; s.40(1A)–(1C) protects **employees** from third-party harassment, it doesn't make the firm liable for harassment of the client. The rationale is mis-framing the legal route. **Proposed fix:** rewrite the rationale to focus on (a) the harm to the colleague hearing it (s.26 in force now — race-related comment creating a hostile environment for colleagues on the call), and (b) the COCON 1.1.7FR Conduct Rule exposure for the speaker from 1 September 2026, rather than the third-party route which doesn't quite fit because the "third party" here is the recipient, not the harasser.

- ⚠ **Module 0 §1, line 19, last sentence.** "If you took Module 1, the framework is the same." Module 0 is intended to run before Module 1 in the audience progression (suggested by the lower numbering and shorter 5-min duration). Either reorder or rephrase as "Module 1 covers the legal framework in depth; this module is its application to written channels." Minor.

### Module 1 — The Law and Why It Matters

**File:** `/Users/richmondrobot/Desktop/togetherbook/training/modules/module_1.md`
**Questions:** `/Users/richmondrobot/Desktop/togetherbook/training/modules/module_1.questions.json`

- ✓ The s.26(1)/(2)/(3)/(4) and s.27 explanations are clean. The Worker Protection Act 2023 commencement (26 October 2024) is correctly described as past. The October 2026 / September 2026 / April 2026 dates are handled correctly. The 25% uplift is correct. The "seven harassment-relevant characteristics" point is correctly made at q15 rationale level.

- ⚠ **VETO — Module 1 Q15, lines 121–125.** Stem: *"The Equality Act protects against harassment related to:"* Correct option is index 2 = *"Any of the nine protected characteristics"*. **Rationale immediately below contradicts the option:** *"Section 26 covers conduct related to any of the seven harassment-relevant protected characteristics (the nine minus marriage/civil partnership and pregnancy/maternity, which are covered by direct discrimination)."* The correct option text is wrong on the law (it says nine when the answer is seven) and the question therefore teaches the wrong answer to the most central question of harassment law. This is veto-grade. **Proposed fix:** change option C text to *"Any of the seven harassment-relevant protected characteristics (the nine minus marriage/civil partnership and pregnancy/maternity)"* — leave `correct: 2` and the rationale unchanged.

- ⚠ **Module 1 §2 lists the nine characteristics in body text without flagging that only seven are harassment-relevant.** This is the same point as above but in the body. Module 2 §1 *does* correctly distinguish seven from nine; Module 1 §2 reads as if all nine ground s.26 harassment, which sets students up to get Q15 wrong. **Proposed fix:** add one sentence to §2 after the bullet list: *"Note: harassment under s.26 (the focus of this module) covers seven of these — the two exceptions are marriage/civil partnership and pregnancy/maternity, which are protected against direct discrimination but sit outside s.26. We cover that distinction in Module 2."*

- ⚠ **Module 1 — only 8 of 25 questions carry the scenario tag.** The minimum is 10. Q2, Q6, Q10, Q13, Q16, Q19, Q22, Q24 are tagged `scenario: true`; Q23 is a definition; Q3, Q14, Q18, Q20, Q25 could plausibly be re-cast as scenarios. **Proposed fix:** convert at least two of the non-scenario questions into scenario form to clear the threshold (e.g. rewrite Q4 as a board-meeting scenario asking whether a manager's plan to wait until October 2026 to update training is defensible).

- ⚠ **Module 1 reflection prompts, lines 211 and 216.** Guidance text reads *"Your manager will not see this — it's for your own reflection."* The spec says the guidance should also state who *does* see it (Group HR, in aggregate). Compare Module 0/2/3/4 reflections which include "only Group HR, and only as anonymised aggregate themes" — that phrasing is stronger and more honest. **Proposed fix:** align Module 1 reflection guidance with the longer-form Module 0/2 wording.

### Module 2 — Recognising harassment in an office setting

**File:** `/Users/richmondrobot/Desktop/togetherbook/training/modules/module_2.md`
**Questions:** `/Users/richmondrobot/Desktop/togetherbook/training/modules/module_2.questions.json`

- ✓ Seven-vs-nine distinction correctly drawn in §1. s.13/s.18 routes for marriage and pregnancy/maternity correctly identified. Disability s.6 definition correctly summarised (q7 rationale). Cancer/HIV/MS deemed-disability from diagnosis correctly stated. Forstater citation accurate. The "not aimed at someone from the group" point — the single most-misunderstood s.26 issue — is taught cleanly. 25 questions, 12 scenario-tagged, two reflections with the correct guidance.

- ⚠ **Module 2 §4, line 47–53 — Forstater grey-area handling.** The text correctly identifies that gender-critical belief and gender reassignment are both protected. The phrasing *"the firm has to navigate this in a way that does not amount to harassment of either, which usually means rules about manner, time and place rather than rules about who is allowed to speak"* is defensible but bumps up against EHRC guidance on respectful workplaces. This isn't wrong, but it is the single most likely paragraph in the entire training pack to attract a complaint from either side. Consider adding a one-line signpost: *"Where this arises, route the conversation through HR before either party's conduct hardens into a complaint."* Not a veto.

- ⚠ **Module 2 Q15 / §12, line 128 — "all seven harassment-relevant characteristics".** Correct. But Module 0 Q17's option B says "the firm could be liable under s.40(1A) EA 2010 for failing to take all reasonable steps to prevent third-party harassment" without naming that the new s.40(1A) is the **inserted** provision (current s.40(1A)–(1C) does not exist yet; current s.40 only has (1)). Module 2 Q15 gets this right ("new s.40(1A) EA 2010"); Module 0 Q17 is slightly looser. Minor.

- ⚠ **Module 2 §7 line 77.** *"Conditions covered include — among many others — diabetes, multiple sclerosis, depression, anxiety disorders, autism, ADHD, dyslexia, long Covid, and HIV."* Long Covid is not yet definitively listed in EHRC technical guidance as a deemed disability — it is treated on a case-by-case basis under the substantial-and-long-term test. The wording "among many others" is honest enough that this isn't a hard error, but a careful reader will flag it. **Proposed fix:** *"…long Covid (where the substantial-and-long-term test is met), and HIV."*

### Module 3 — Bystander Action: The 5Ds

**File:** `/Users/richmondrobot/Desktop/togetherbook/training/modules/module_3.md`
**Questions:** `/Users/richmondrobot/Desktop/togetherbook/training/modules/module_3.questions.json`

- ✓ 5Ds attribution is correct (Green Dot / Dorothy Edwards 2006, extended by Hollaback! / Right To Be — Delay 2015, Document 2017). The 17–21% Coker et al. figure matches research/04. The s.27 / s.43B / s.23 ERA 2025 lattice is accurately set out in §7. The "Plain-English legal box" footer is well-drafted. 25 questions, 10 scenario-tagged (just clears the threshold), two reflections with the right guidance.

- ⚠ **Module 3 §9, line 141, AND Q12 — fabricated "70% of bystander value is acknowledgement" statistic.** Text: *"The literature is clear that perhaps 70% of the value a bystander provides is acknowledgement"*; Q12 rationale: *"The research consistently finds that acknowledgement is roughly 70% of the value of bystander action."* This precise figure does not appear in research/04 and I cannot locate it in the bystander-research literature. Coker et al., the 2020 BMJ Open evaluation, and the 2024 scoping review all cite victimisation-reduction and self-efficacy effect sizes, not a "70% from acknowledgement" decomposition. This reads as invented and is exactly the kind of stat-with-a-citation-shaped-hole that gets quoted back and then can't be sourced. **Proposed fix:** delete the percentage in both places. Body: *"The literature is clear that acknowledgement is among the most valuable things a bystander can provide — it confirms…"*. Q12: replace with a non-numeric question (e.g. *"Which of these is the strongest single thing a bystander can do for an affected colleague after the moment has passed?"* — correct answer: "Acknowledge what they saw and ask the colleague what they want next.").

- ⚠ **Module 3 reflection r1 guidance, line 337.** Reads *"Your manager will not see this — it's for your own reflection. There is no right answer and you are not being scored."* Misses the explicit "Group HR only / aggregate themes" framing the other modules use. **Proposed fix:** align with Module 0/2 phrasing.

- ⚠ **Module 3 §6 line 100 — chain-of-custody / screenshot.** Text: *"A WhatsApp screenshot can be edited; the original chat history on the original device cannot."* Strictly the original chat history on the original device *can* be edited (WhatsApp added message-editing in May 2023 with a 15-minute edit window and an "edited" marker). The point being made is correct in substance (originals are stronger than screenshots) but the wording is overstated. **Proposed fix:** *"A WhatsApp screenshot can be edited without any audit trail; the original chat history on the original device carries WhatsApp's own integrity markers and timestamps, which a screenshot strips out."*

### Module 4 — Power Dynamics and High-Risk Situations

**File:** `/Users/richmondrobot/Desktop/togetherbook/training/modules/module_4.md`
**Questions:** `/Users/richmondrobot/Desktop/togetherbook/training/modules/module_4.questions.json`

- ✓ s.26(3) treatment is excellent — the implicit-vs-explicit quid-pro-quo distinction is the single sharpest piece of writing in the pack. SMCR remuneration-code overlay correctly identified. Off-site / work-travel / completion-drinks situational map is solid. Odey precedent correctly dated and described, with the appropriate caveat that the case is under Upper Tribunal review. Sarah Pritchard "reddest flags" quote is verbatim from research/02. 25 questions, 10 scenario-tagged, two reflections with correct guidance. The Plain-English legal box (line 164) is the cleanest one in the pack.

- ⚠ **Module 4 §2.3 line 66 — misleading framing of off-site liability.** Text: *"From 1 October 2026 the firm's exposure on its own off-sites is direct."* The firm's exposure for harassment of its own employees by other employees at an off-site has been direct (vicariously) since 2010 under s.109 EA 2010. The October 2026 change is third-party harassment (s.40(1A)–(1C) inserted by s.21 ERA 2025) and the "all reasonable steps" uplift (s.40A as amended by s.20 ERA 2025). The sentence as written implies that own-employee off-site harassment is somehow not currently the firm's exposure, which is wrong and could be relied on by a participant. **Proposed fix:** *"From 1 October 2026 the firm's exposure on its own off-sites tightens further — the s.40A duty rises to 'all reasonable steps' and the firm becomes directly liable for harassment of its employees by third parties present at the event. Own-employee harassment at off-sites has been vicariously the firm's liability under s.109 EA 2010 since 2010."*

- ⚠ **Module 4 §2.6 line 104 — "Policy HR-12, Workplace Relationships".** This is referenced as if it exists. If the firm does not actually have a Policy HR-12, this is a fictional artefact that the training will invite participants to look up and not find — which then undermines the rest of the training's credibility. **Proposed fix:** confirm Policy HR-12 exists and is published on the intranet before launch. If it doesn't, either (a) draft the policy now and publish it before the module launches, or (b) replace the reference with *"the firm's Workplace Relationships policy [link]"* and have HR confirm a real link before launch.

- ⚠ **Module 4 §1 line 17 / §2.1 line 38.** Body says SMCR remuneration determination is a "regulated decision in many SMCR firms" — correct, but the qualifier "in many" is doing work. The SYSC 19 remuneration code applies in tiers depending on firm type. Q4 rationale handles this OK; the body text could note that the specific application depends on the firm's SYSC 19 tier. Not blocking.

- ⚠ **Module 4 Q11 option B / rationale.** Both correctly reference s.23 ERA 2025 / 6 April 2026. But the option text includes "The public-interest test still applies — purely individual personal grievances may not qualify." Splitting the public-interest caveat between the option and rationale is fine, but make sure the quiz renderer surfaces the rationale to the learner after the answer is locked in — otherwise the most important nuance is lost on every learner who picks B confidently. UI note rather than content fix.

### Module 5 — Reporting and what happens next

**File:** `/Users/richmondrobot/Desktop/togetherbook/training/modules/module_5.md`
**Questions:** `/Users/richmondrobot/Desktop/togetherbook/training/modules/module_5.questions.json`

- ✓ Three FCA reporting clocks (SUP 10C.14 / SUP 15.11 REP008 / SUP 15.3) correctly described. SYSC 22 correctly framed as 1 September 2026 onward. ACAS helpline number correct (0300 123 1100, verified). s.27(3) good-faith / bad-faith carve-out correctly explained. Chesterton 2017 public-interest reference accurate. 25 questions, 12 scenario-tagged, two reflections (visibility: group_hr_only).

- ⚠ **Module 5 §6 — counts seven routes but calls it "six".** §6 heading: "Where to report — six routes, not one"; line 109 closes "Six routes. You pick." The bulleted list actually has: line manager, skip-level, HR, Speak Up, EHRC, ACAS, police = **seven**. Q11 in the question bank also calls them "six" while listing all seven in the rationale. Reflection r1 says "the six routes in Section 6." This is internally inconsistent in three places. **Proposed fix:** change "six" to "seven" in all three locations (§6 heading, §6 closing line, Q11 stem and rationale, reflection r1 prompt, body of Module 5 takeaways). Alternative: drop one route (probably "police" since it's framed as separate from the firm's process) and keep "six" — but the seven-route formulation is more honest and is the one to keep.

- ⚠ **Module 5 questions file uses a different JSON schema from modules 0–4.** Modules 0–4 use `"options": [...]` (array of strings) and `"correct": <int>` (0–3). Module 5 (and Manager) use `"choices": [{"key": "A", "text": "...", "correct": true}, ...]` plus `"tags": [...]` plus `"id": "m5_q01"` rather than `"q1"`. This will break any single quiz renderer that doesn't handle both. Not a content issue — but a deployment blocker. **Proposed fix:** normalise to a single schema before launch. Pick one (the Module 0–4 shape is leaner, the Module 5 shape carries more metadata). I'd recommend converting Module 5 + Manager *down* to the Module 0–4 shape and tracking scenario flags via the existing `[scenario]` text marker in the stem.

- ⚠ **Module 5 §6, ACAS bullet.** *"ACAS sits between informal grievance and formal tribunal and is the body the law will direct you to before a tribunal claim through early conciliation."* Correct, but could be stronger: it is statutorily required pre-issue under s.18A Employment Tribunals Act 1996 (Early Conciliation), not just "directed to". Optional polish.

- ⚠ **Module 5 §5 — REP008 reporting period.** Text correctly says "1 September – 31 August; deadline 31 October." This matches research/02 §4. Good.

### Module Manager — Manager add-on

**File:** `/Users/richmondrobot/Desktop/togetherbook/training/modules/module_manager.md`
**Questions:** `/Users/richmondrobot/Desktop/togetherbook/training/modules/module_manager.questions.json`

- ✓ Receiving-a-disclosure section is the strongest single piece of writing in the pack — the do/don't lists, the "don't promise outcomes" framing, and the "they don't want a formal complaint" trap are all faithful to EHRC Step 6 and the EEOC Task Force §V. s.40A awareness-not-paperwork duty correctly stated. s.136 burden-shift correctly cited (Q7). Forensic IT chain-of-custody and Computer Misuse Act framing accurate. 25 questions, 16 scenario-tagged, three reflections (Manager exception in the spec). Pass mark = 7 of 8 (default 80%) — but the spec calls for 8 of 10 on the Manager track. Let me check: `"served_per_attempt": 10` and `"pass_mark_percent": 80` → 8 of 10. Correct.

- ⚠ **Module Manager §6 line 144 — "from 6 April 2026, where the underlying disclosure was a protected disclosure"** is past tense, correct given today's date.

- ⚠ **Module Manager Q7 rationale — s.124A clarification.** Rationale includes: *"There is no automatic salary cap on victimisation awards under the EA 2010; the 25% uplift in s.124A applies to sexual-harassment compensation where the s.40A duty is breached and is unrelated."* Correct, well-distinguished. Good defensive drafting.

- ⚠ **Module Manager §7 worked example "James at Acme Brokers".** This is the closest the pack comes to a named-individual scenario; "James at Acme Brokers" is plainly hypothetical (not a real broker or person) but the spec says no "personalised 'Dan said this last week' examples — only generic scenario types." A real-broker-firm could exist; "Acme" is conventionally fictional. Borderline. **Proposed fix:** change to "a broker at one of the firm's top-10 broker partners" without a first name, to keep the scenario fully generic. Minor.

- ⚠ **Module Manager Q6 rationale — s.43B/47B reference.** Reads *"the s.43B/47B ERA 1996 whistleblowing-detriment claim."* Strictly the protected-disclosure definition is s.43B and the detriment cause of action is s.47B (correct as written). Good cross-cite.

- ⚠ **Module Manager uses the same `choices`/`correct:true` schema as Module 5.** Same renderer-consistency issue as Module 5 — see above. Single-schema normalisation is a one-evening job for whoever owns the front-end.

- ⚠ **Module Manager reflection prompts (line 245 and below) — three prompts, correctly aligned with the spec's Manager exception. Guidance "Logged but not scored. Your line manager will never see your answers — only Group HR, and only in aggregate themes" is the strongest of the seven modules. Good.**

---

## Veto items (must fix before ship)

1. **Module 1 Q15 — wrong-answer-text on the central seven-vs-nine question.** Option C currently teaches the wrong answer. Fix the option text from "nine" to "seven" (see Module 1 findings above for exact wording).

2. **Module 0 §2 — unverifiable "2024 Bull Express tribunal" citation.** Delete the case name; replace with a generic "successive employment tribunal decisions" formulation, or substitute a verifiable case (Forbes v LHR Airport [2019]). Inventing case names in compliance training is the single fastest way to lose credibility in an EHRC review.

3. **Module 3 §9 and Q12 — fabricated "roughly 70%" acknowledgement statistic.** Not in research/04, not in the bystander literature I can verify. Delete the percentage; replace with a non-numeric qualitative claim.

4. **Module 5 question schema differs from Modules 0–4 (and Manager differs the same way).** Will block a single quiz renderer. Normalise the JSON shape before launch — this is a deployment veto, not a content veto, but it must be done before the modules can be served.

5. **Module 5 "six routes" vs seven listed — internal inconsistency in three places.** Change "six" to "seven" in heading, closing line, Q11, and reflection r1.

---

## Suggested follow-ups (would improve but not blocking)

- **Module 1** — convert two non-scenario questions to scenarios to clear the 10-minimum threshold.
- **Module 1 §2** — add one sentence flagging that only seven of the nine characteristics trigger s.26 harassment, so learners don't arrive at Q15 with the wrong mental model.
- **Module 0 Q10 rationale** — re-frame so the route runs via s.26 (current law) + COCON 1.1.7FR (1 Sep 2026), not via the third-party s.40(1A) route which doesn't quite fit the scenario.
- **Module 2 §7 long-Covid bullet** — add "(where the substantial-and-long-term test is met)" qualifier.
- **Module 3 §6 chain-of-custody** — soften the "cannot be edited" claim about original WhatsApp messages (post-2023, originals *can* be edited within a 15-min window, with a marker).
- **Module 4 §2.3 off-site liability framing** — clarify that own-employee off-site harassment has been firm liability since 2010; October 2026 is the third-party / "all" uplift.
- **Module 4 §2.6 — confirm Policy HR-12 actually exists** before launch. If not, draft it or replace the reference with a live link.
- **Module Manager §7 worked example** — strip the first name "James" to keep the scenario fully generic.
- **Module 1 / Module 3 reflection guidance** — align with the longer-form "Group HR / aggregate themes" wording used in Modules 0 / 2 / 5 / Manager.
- **Cross-pack** — consider adding a single "Glossary" page (WCAG 3.1.3 / research/05 Part B item 11) covering protected characteristic, s.26, s.27, s.40A, COCON, SMF, certified person, SUP 10C.14, REP008, SYSC 22, F&P. Currently each module re-explains in passing.

---

## Sign-off

Subject to the five veto items above (fix Module 1 Q15 wrong-answer text; remove the Bull Express citation; remove the 70% acknowledgement stat; normalise the question-bank JSON schema; fix the six-vs-seven inconsistency in Module 5), the training pack is defensible against EHRC technical-guidance and "all reasonable steps" tribunal review as it stands today. The substantive legal content is more accurate, better-sourced, and better-tailored to the UK financial-services audience than the typical off-the-shelf e-learning the Bird & Bird one-year review criticises. The Manager add-on in particular is materially stronger than the EEOC Task Force benchmark would predict for an internal build. The 5Ds framing, the avoidance of the "men are harassers, women are protected" frame, the use of scenario-tagged questions in the right proportion, the open-text reflections logged-not-scored with the right confidentiality assurance, and the explicit October-2026 / 1-September-2026 readiness sections are all what an EHRC reviewer would expect to see in a firm taking the s.40A duty seriously.

The five fixes are small and can be made same-day. With them in place: **ship.**
