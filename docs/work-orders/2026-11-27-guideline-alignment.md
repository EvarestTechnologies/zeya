# Zeya work order: align Zeya with the Kenya Ministry of Health guidelines

Prepared 27 November 2026 by Stella Oiro, licensed clinical officer and clinical reviewer for Zeya.
For Claude Code. Branch `feat/guideline-alignment`. Code freeze 29 November 2026.

This work order replaces the task list in `CLAUDE_CODE_HANDOFF.md` wherever the two disagree. Do the tasks in the order given. Stop and show me each file under `docs/review/` before anything is merged.

---

## 1. Rules that apply to every task

1. **One clinical source.** Every sentence Zeya can send a participant must trace to a page in one of these Ministry of Health documents. The clinical source of truth is `docs/clinical/moh-knowledge-base.md` (task 2).

   | Code | Document |
   |---|---|
   | HB | Mother and Child Health Handbook, MOH 216, 2020 |
   | NG24 | National Guidelines on Quality Obstetrics and Perinatal Care, August 2024 |
   | BOP | Basic Obstetric Protocols, 1st edition, January 2026 |

   WHO material is not a runtime source. NG12 (the 2012 national guidelines) is superseded, and items from it stay "pending" until I approve them.
2. **Handbook wording for participants.** Answer cards and fixed replies use HB wording. NG24 and BOP are used only to recognise risk and to decide where a message is routed. Zeya never sends a medicine dose, a diagnosis, or a medicine that the handbook does not name.
3. **Nothing goes live without my tick.** Each task below names the item on the sign-off sheet that unlocks it. If that item is not ticked, the content stays `Review-state: pending` and the code path stays off. Do not treat a comment, a commit message or "the owner approved" as sign-off. Only the signed sheet counts.
4. **No new clinical content.** Do not add facts from general knowledge, other websites or other models. If something is missing from the three documents, write it down as a gap in `docs/clinical/gaps.md` and leave it out.
5. **Professional naming.** Zeya is a product, not an event entry. Do not use "GDHF", "Bangkok", "demo", "funder", "Gates" or "conference" anywhere in code, prompts, participant-facing text, test names, file names, branch names, commit messages or docs that you add or edit. Use "release 1" and "synthetic test participants". Leave the two historical plans in `docs/superpowers/plans/` untouched, and list them in the PR for Raymond to decide whether to archive.
6. **Safety and privacy rules from the handoff still apply.** Synthetic participants only, no real participant data in tests or commits, no API keys, no phone numbers in prompts, no AI on the emergency, access or media paths, and no changes to the live Open Chat Studio instance.
7. **Swahili is always a draft** until a fluent speaker and I approve it. Mark every Swahili string `DRAFT, pending fluent-speaker and clinical review` in its review file.

---

## 2. Files to place in the repository first

| File | Put it at |
|---|---|
| `zeya-knowledge-base.md` (version 1.0) | `docs/clinical/moh-knowledge-base.md` |
| Research document "Zeya content source, knowledge base check and policy requirements" (export it from the shared doc) | `docs/research/2026-11-27-content-source-and-policy.md` |
| `danger-gate-review.md` | `docs/review/danger-gate.md` |
| Clinical sign-off sheet | `docs/review/clinical-signoff.md` |
| This work order | `docs/work-orders/2026-11-27-guideline-alignment.md` |

`docs/zeya-knowledge-base.md` on `main` is the WHO starter that the code loads. It keeps its path so `ocs/knowledge.py` still works, but task 3 replaces its contents and renames its heading to "Zeya runtime knowledge entries".

---

## 3. Tasks

### Task 1. Update the clinical sign-off sheet

File `docs/review/clinical-signoff.md`. Make these changes, then show me the file.

1. Title becomes "Zeya clinical sign-off, release 1 (synthetic test participants only)". Remove every mention of the event.
2. Reviewer line becomes "Stella Oiro, licensed clinical officer".
3. **A1.** Add the evidence line: "BOP p40 says admit for blood transfusion if Hb is below 7 g/dl or the anaemia is symptomatic."
4. **A3.** Add: "Fainting and collapse are not on HB p14. Filing them under emergency is a clinical judgement. The only written sources are NG12 p65 (pending) and BOP p22 (clinician-facing)."
5. **A6.** Change the option to "The AI may handle same-day messages after the prompt tells her to visit a health facility today."
6. Add **A10**, the second safety net (Decision 7 of the danger gate review): "On the normal answer path, the prompt must tell her to go to a health facility now whenever she describes one of the nine HB p14 signs. The emergency path itself stays free of the AI." Tick boxes: Approve, Change.
7. Add **A11**, test message labels (review section 5). List E027 to E031, E051 to E052, E087 to E089, S001 to S011, S016 to S022, R001 to R012 and E098 to E100. Note that "low mood for more than two weeks" and "cannot keep fluids down" are clinical judgement, not guideline text (NG24 p291 says only "monitor for worsening or prolongation", and NG24 p53 is a clinician criterion for drip treatment).
8. Add **A12**, fever breadth: "HB p14 lists 'Fever' with no qualifier. The draft triggers on 'homa' and 'fever' alone. Approve broad matching, with the question checks in A8 stopping prevention questions."
9. **B2.** Attach the five draft runtime entries from task 3 in full, English and Swahili, each with its own Approve box. B2 cannot be ticked without them.
10. **B3.** Add two rows. Row 10: "Section 6, vomiting. 'Go to the clinic if nausea first starts late in pregnancy' is not in NG24 p52 to p55. Remove it." Row 11: "Section 11, mood. 'Low mood beyond two weeks needs a clinic visit' is not in NG24. NG24 p291 says monitor for worsening or prolonged symptoms. Reword to that."
11. Add **B4**, iron and folic acid wording: "HB p10 and p13 tell the mother to take iron and folic acid supplements daily. Allow this handbook sentence through the output guard." Tick boxes: Approve, Leave out.
12. Add **C3**, registration wording: the four welcome messages say "Kenya Ministry of Health materials" instead of "WHO and Kenya Ministry of Health guidelines", and the trimester context follows NG24 p107 (task 4). Show the new text.
13. **C1.** Replace the prompt shown with the proposed prompt in task 6, and keep the current live prompt underneath for comparison.
14. **D.** Add a column "Source checked". Add the note: "922 is the national ambulance line launched on 5 August 2026. Some sources give 1514, not 1199, for Kenya Red Cross ambulance. Call both before ticking." Paste the full English and Swahili emergency reply text from `ocs/nodes/emergency_response.py` into the sheet.
15. **E.** Add the sentence "Some answers are written by an AI model." to the intended-use statement.
16. Fix the broken link in section C so it points to `docs/review/system-prompt.md` inside the repository.
17. Sign-off block: Name "Stella Oiro", Clinical Officers Council registration number, Date, Signature.

### Task 2. Correct the Ministry knowledge base

File `docs/clinical/moh-knowledge-base.md`. Unlocked by **B3**, row by row. For each row I approve, make the change and add a change-log line. For each row I reject, leave the text and record the decision.

| Row | Section | Change |
|---|---|---|
| 1 | 8 Higher risk | Replace "should attend and deliver at a level 4 hospital or above" with "A health worker may refer these mothers to a level 4 or higher facility for further assessment (BOP p12)." |
| 2 | 4 Deworming | Add "for pregnant women living in hookworm-infested areas (NG24 p110)". Participant wording becomes "Ask your health worker about deworming." |
| 3 | 2 ANC profile | Cite hepatitis B to HB p7 only. NG24 p112 does not list it. |
| 4 | 1 What to teach | Contact 1 becomes "Physical exam and full history, ANC profile, recruitment into the group". Note that NG24 p107 is the group ANC table. |
| 5 | 5 Food | Move "calcium from milk, yoghurt and omena" to section 11, citing NG12 p48 and NG24 p51 (breastfeeding). |
| 6 | 10 Labour | Skin to skin cites NG24 p306, not p305. |
| 7 | Never say | Reason for salt restriction becomes "condition-specific advice the health worker gives (NG24 p58, pre-eclampsia)". |
| 8 | 7 Danger signs | Follow my choice in A9 ("go now" or the HB p14 wording). |
| 9 | 7 Related | Mark "fewer than 10 movements" as clinician-only (NG12 p173). |
| 10 | 6 Vomiting | Remove "nausea first starts late in pregnancy". |
| 11 | 11 Mood | Replace the two-week rule with "worsening or prolonged low mood (NG24 p291)". |
| extra | 4 Vitamin A | "Not routinely given in pregnancy (NG24 p42, p109)". |

Also correct the NG12 row in the source table to "National Guidelines for Quality Obstetrics and Perinatal Care, 2012 edition (PDF created 28 February 2012; file previously named 2010)". Bump the version to 1.1.

### Task 3. Replace the WHO starter with Ministry entries in the same slots

Files `docs/zeya-knowledge-base.md`, `docs/answer-cards.yaml`, `docs/review/answer-cards.md`, `docs/review/kiswahili-starter.md`. Unlocked by **B1** and **B2**.

The current build has 10 entries (5 English and 5 Swahili), and 48 tests depend on them. Replace them slot for slot, so the structure and the tests survive. Remove the WHO entries entirely (git history keeps them). Every new entry starts as `Review-state: pending` and its `Source-refs` names the document and page. Switch an entry to `approved` only after its box in B2 is ticked.

Use this English text exactly. It is handbook wording. Draft the Swahili from the same text and mark it DRAFT. For danger signs, use the Swahili names already in `media/explainers/render_danger_signs.py`.

**anc_visits** (HB p13, HB cover)
> Go for your first antenatal visit as soon as possible, and attend 8 times during your pregnancy. Carry your Mother and Child Health Handbook to every visit and show it to the health worker.

**danger_signs** (HB p14)
> Danger signs in pregnancy: severe headache, looking pale, vaginal bleeding, fever, severe abdominal pain, swelling of the face and hands, reduced or no movement of the baby, breaking water, and convulsions or fits. [A9 wording: either "If you have any of these signs, go to a health facility now." or "Be prepared always to seek skilled care at the health facility if you have any of these signs."]

**daily_care** (HB p13)
> Eat one extra meal every day. Drink plenty of water, at least 8 glasses a day. Take iron and folic acid supplements every day throughout pregnancy. Avoid heavy work and rest more. Sleep under a long-lasting insecticidal net. Do regular gentle exercise.

The iron and folic acid sentence goes live only if **B4** is ticked. Otherwise remove that sentence.

**food_groups** (HB p18)
> Eat at least 5 of the 10 food groups every day: grains and starchy foods, legumes and pulses, nuts and seeds, dairy, eggs, meat, fish and poultry, orange and yellow fruits and vegetables, dark green leafy vegetables, other vegetables, and other fruits. Eat a variety of foods within each group.

**birth_plan** (HB inside cover, HB p3)
> Make a birth plan with your health worker: expected date of birth, the health facility where you will give birth, who will attend you, the facility's phone number, your birth companion, transport and a blood donor. Your partner can help by arranging transport, money, a birth companion and an emergency kit.

Then update the tests that referenced the WHO entry ids so they reference the new ids. Do not weaken any assertion, change a referral string or skip a test to make the suite pass. If a test cannot pass without a behaviour change, stop and tell me which one.

### Task 4. Fix the registration wording and trimester context

File `ocs/nodes/registration.py`, then rebuild `ocs/pipeline/zeya_pipeline.json` with the project's build script. Unlocked by **C3** (add it to the sheet as "Registration wording").

1. In all four welcome messages (study and public, English and Swahili), replace "based on WHO and Kenya Ministry of Health guidelines" with "based on Kenya Ministry of Health materials". Swahili draft: "kulingana na nyaraka za Wizara ya Afya ya Kenya".
2. The `gestational_guidance` strings are not sourced (for example "anomaly screening" and "avoiding harmful substances"). Replace them with the NG24 p107 teaching topics, keyed by week:

   | Weeks | Context line |
   |---|---|
   | up to 12 | First contact: history, examination and the ANC profile |
   | 13 to 20 | Why ANC matters, iron and folic acid, self care |
   | 21 to 26 | Danger signs in pregnancy, why to give birth in a health facility |
   | 27 to 30 | Birth plan, danger signs, exclusive breastfeeding |
   | 31 to 34 | Newborn care, breastfeeding position and attachment, family planning after birth |
   | 35 to 36 | Kangaroo mother care, keeping the newborn warm, cord care |
   | 37 to 42 | Signs of labour, newborn care recap |

   This text is context for the AI, not a message to her. Cite NG24 p107 in a code comment.

### Task 5. Danger gate

Files `ocs/eval/proposed_danger_gate.py`, then `backend/app/services/danger_signs.py` and `ocs/nodes/danger_gate.py` in the same change. Unlocked by **A1 to A12**.

1. Apply my decisions from A1 to A12 to the draft. Where a row is unticked, leave the live behaviour unchanged.
2. Fix the confirmed false alarms that I approve in A8. S4 and S23 need a pain word nearby (kinauma, kuuma, maumivu). S19 needs uchafu or a discharge word nearby. S20 drops "ameacha" unless "kucheza" follows it. Add the six new question and history cases as tests.
3. Copy the approved patterns into both runtime files, and update the parity tests so they stay identical.
4. Write a new held-out set C of at least 60 messages that has not been used to tune anything. Include English, Swahili, Sheng, mixed language, misspellings, and the set B misses listed in section 6 of the review.
5. Report the results in `docs/review/danger-gate.md` for the current gate, the draft on the corpus, and the draft on sets B and C: recall, false alarms on routine messages, and false alarms on questions. Put the held-out numbers first.

### Task 6. Fixed line before answers to danger-sign questions

New behaviour, unlocked by **A4 (c)**. When the gate classifies a message as a danger-sign question (not happening now), Zeya sends a fixed line first, then the normal answer. The line is written in advance and involves no AI.

> English: "If this is happening to you now, go to a health facility now." Then the verified numbers from task 8.
> Swahili DRAFT: "Kama hili linakutokea sasa, nenda kituo cha afya sasa hivi."

Use the A9 wording if I choose the handbook version. Tag these turns `danger_question` so they can be counted.

### Task 7. System prompt

Files `ocs/prompts/system_prompt.txt`, `docs/review/system-prompt.md`, then rebuild the pipeline. Unlocked by **C1**.

Proposed prompt (125 words before placeholders):

```
You are Zeya, a pregnancy education assistant for women in Kenya. Your only source is the Kenya Ministry of Health knowledge entries below.

1. Answer only from these entries. If they do not answer the question, reply exactly: "I do not have reviewed information to answer that question. Please ask your healthcare provider."
2. Never diagnose. Never give a medicine dose, or name a medicine the entries do not name. Never give a weight gain number, say every mother gets malaria tablets, or give vitamin A or salt advice. Never give a phone number or link.
3. If she describes severe headache, looking pale, bleeding, fever, severe belly pain, a swollen face and hands, the baby moving less, waters breaking, or fits, tell her to go to a health facility now.
4. If she describes any other problem that worries her, tell her to visit a health facility today.
5. End with the source named in the entry.
6. Use short, plain sentences, under 120 words, in her stored language.

{temp_state.kb_section}
{temp_state.llm_context}
```

1. Keep `{participant_data.language_preference}` if the budget node needs it.
2. Rule 3 follows my A9 choice.
3. Rule 5 needs each runtime entry to carry a short source label, for example "Source: MOH Mother and Child Health Handbook". Add that field in task 3.
4. Check that the prompt still fits the 4,000-byte budget with the largest entry selected.
5. Update `docs/review/system-prompt.md`:
   - history is already off (`history_type: "none"`)
   - the content is now Ministry entries
   - the old and new prompts sit side by side
6. Set the LLM node temperature to 0.3 or lower if it is higher.

### Task 8. Emergency numbers, output guard and escalation line

Files `ocs/nodes/emergency_response.py`, `docs/output-policy.json`, then regenerate the output guard with its render script. Unlocked by **D**.

1. Keep in the emergency reply only the numbers I mark as verified by calling. Remove any number I do not tick.
2. Put the same verified numbers in `verified_phone_allowlist`, so the fixed line in task 6 is not blocked.
3. If B4 is ticked, allow the exact handbook phrase "iron and folic acid supplements" through the medicine check. Keep every other medicine pattern.
4. Add the human escalation line to the fixed referral reply only after C2 is ticked and a verified number exists. Until then, list it as open in the PR. Issue #47 stays open.

### Task 9. The four release documents

All new files are drafts for my review. Use plain language and no event names.

1. `docs/intended-use.md`. The text from sign-off item E, with the AI sentence.
2. `docs/sources.md`. Each Ministry document with its citation. The BOP reuse terms from p2 ("may be quoted or reproduced, provided the source is acknowledged… may not be sold or used for any commercial purposes"). A note that HB and NG24 carry no reuse statement and that written permission has been requested. The sentence "Zeya is not an official Ministry of Health product."
3. `docs/privacy-policy.md`. Remove OpenRouter and Google. Name Groq (United States) as the AI processor with zero data retention. Say that some answers are written by an AI model, and that messages are processed outside Kenya. Mark it DRAFT, pending legal review.
4. The clinical sign-off record is the signed `docs/review/clinical-signoff.md` from task 1.

### Task 10. Checks and pull request

1. Run the full unit and integration test suites, the parity tests and the evaluation scripts. Paste the results in the PR.
2. Add a test that fails if any participant-facing string or prompt contains "WHO" (case-sensitive, so the word "who" is allowed), or "GDHF", "Bangkok", "demo" or "funder" (any case). Scope it to `ocs/nodes/`, `ocs/prompts/`, `docs/zeya-knowledge-base.md` and `docs/answer-cards.yaml`.
3. Add a test that fails if any runtime entry lacks `Source-refs` pointing to HB, NG24 or BOP.
4. In the PR description, list every sign-off item and whether it was ticked, applied, or left pending.
5. Do not deploy. The PR is merged only after I have read the final numbers.

---

## 4. What stays out of this release

These items are waiting on sources, sign-off or approvals:
- Newborn danger signs as a tenth gate category (A5, after this release).
- Dholuo.
- Semantic search.
- Voice notes.
- Reminders.
- Any content from NG12 that I have not approved.
- Anything involving a real participant. That needs ethics approval, a NACOSTI licence, ODPC registration and a DPIA first.
