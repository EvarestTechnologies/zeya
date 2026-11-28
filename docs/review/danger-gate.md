# Danger gate review: proposed patterns and corpus labels

**For:** Achar (clinical officer). Sign-off is needed before any change to the live danger gate.
**Status:** Proposal. The live gate is unchanged. The draft is in `ocs/eval/proposed_danger_gate.py` and is not used by the pipeline.
**Date:** 12 November 2026, numbers refreshed 27 November 2026
**Clinical source:** your Ministry of Health knowledge base, `docs/zeya-knowledge-base.md` on this branch. Every rule below cites a section of it.

When you approve or change an item, write your decision next to it: **Approve**, **Change to …** or **Remove**. Your decisions are also collected in `docs/review/clinical-signoff.md`.

---

## 0. Results after sign-off (27 November 2026)

Your decisions A1 to A12 are applied. The approved draft is now the live gate in both `ocs/nodes/danger_gate.py` and `backend/app/services/danger_signs.py`. The two files are identical, and the parity tests enforce it.

**Held-out sets first.** No pattern was tuned on these.
- **Set B:** 50 messages, written 12 November.
- **Set C:** 63 messages, written 27 November, after the decisions and before any pattern change. Set C includes the 14 set B misses.

| Set | Gate | Emergencies caught | Routine false alarms | Question false alarms |
|---|---|---|---|---|
| B | Before (on `main`) | 0/30 (0%) | 0/20 (0%) | n/a |
| B | After | **15/30 (50%)** | 1/20 (5%) | n/a |
| C | Before (on `main`) | 4/39 (10%) | 0/15 (0%) | 1/9 (11%) |
| C | After | **14/39 (36%)** | 1/15 (7%) | 1/9 (11%) |

**Corpus.** 310 messages. Batch v1 was looked at while the patterns were written, so it is not a fair test.

| Measure | Before | After |
|---|---|---|
| Emergencies caught, all (132) | 14 (11%) | 108 (82%) |
| Emergencies caught, v2 only (40) | 2 (5%) | 16 (40%) |
| Routine false alarms (140) | 5 (4%) | 0 (0%) |
| Questions about danger signs sent to emergency (22) | 4 (18%) | 0 (0%) |
| Same-day messages sent to emergency (28) | 0 | 0 |
| The walkthrough phrase "nina homa na kichwa kinauma sana" | missed | caught |

**The target is not met.** The work order asks for at least 95% of emergencies caught, with under 10% false alarms. On unseen wording the gate catches 36 to 50%.

What it still misses, from set C:
- **Spelling mistakes:** "im bleading", "my waters brok", "my hed is paining".
- **New wording:** "worst headache of my life", "I am burning up", "soaked with water", "foaming at the mouth".
- **Sheng:** "Bebi hachezi siku nzima", "Maji imevunja", "Ako na fits".

No pattern was added for these, because only the approved S1 to S29 patterns and the A8 fixes were applied. Each new pattern needs your sign-off first. The second safety net in the AI prompt (A10) covers the normal answer path.

**Remaining false alarms:**
- **"I want to donate blood after delivery"** (set B) and **"the clinic took my blood for tests"** (set C) still trigger "blood". The live gate always flagged these and still does.
- **"is fever dangerous in pregnancy?"** (set C) is sent to emergency, because the question check does not cover "is … dangerous". The gate on `main` did the same.

**What changed while applying the decisions:**
1. **A8 fixes.** S4 and S23 need a pain word nearby, before or after the body word. S19 needs uchafu or a discharge word. S20 drops "ameacha" unless "kucheza" follows. All 12 reported false alarms are now safe.
2. **Context rules.** A question about what the clinic checks, a past pregnancy, or blood from the gums, nose or food is treated as a question or history, not happening now. These messages take the normal route, and task 6 adds the fixed line.
3. **Bug fixed in S28.** "anguka … tetemeka" had a word boundary before "anguka", so it missed prefixed verbs such as "Alianguka". The boundary is removed, as your S28 row intends.
4. **Pain word placement.** The S4 fix at first required the pain word after "kichwa", which lost "Naumwa na kichwa sana" (E015). The pain word may now come before or after.

Reproduce:

```
python -m ocs.eval.score_heldout --details
python -m ocs.eval.score_gate
```

---

## 0b. Typo tolerance and near misses (28 November 2026, draft only)

Drafted in `ocs/eval/proposed_danger_gate.py` and awaiting sign-off items A13 and A14. The live gate is unchanged.
- **Set D** (61 messages) was written and committed before these changes, so it is the fair test.
- **Set C** was used to choose the near-miss patterns, so its new score is not evidence.

| Set | Live gate | Draft with A13 and A14 |
|---|---|---|
| **D, emergencies caught (39)** | **28 (72%)** | **33 (85%)** |
| D, routine false alarms (12) | 0 | 0 |
| D, question false alarms (10) | 3 | 3 |
| C, emergencies caught (39), tuned | 14 (36%) | 37 (95%) |
| B, emergencies caught (30) | 15 (50%) | 29 (97%) |
| Corpus, emergencies caught (132) | 108 (82%) | 118 (89%) |
| Corpus, routine false alarms (140) | 0 | 0 |

New false alarms found by probing:
- "I am so hot in this weather" (A14 row 10)
- "what does it mean if I see spots?" (set C question; A14 row 6)

Reproduce:

```
python -m ocs.eval.score_heldout --node ocs/eval/proposed_danger_gate.py --details
```

---

## 1. Summary

When a mother's message matches a danger sign pattern, Zeya sends the emergency reply and the emergency numbers right away, with no AI step. Today the live gate has 39 patterns in 8 categories. It sends the walkthrough's emergency message, "nina homa na kichwa kinauma sana", down the safe route.

The draft adds:
- about 95 patterns, in English, Swahili and Sheng
- a ninth category, **pallor_anaemia**, for "looking pale" (HB p14)
- a check so that general questions about danger signs get a normal answer, not an emergency alarm

Test set: `ocs/tests/danger_eval_corpus.csv`, 310 messages (#20). Batch v1 is the first 200 messages, which I looked at while writing the draft. Batch v2 is 110 messages added later, which no pattern was tuned on.

| | Live gate | Draft gate |
|---|---|---|
| **v2 only (never tuned on)** | | |
| Emergencies caught (40) | **2 (5%)** | **16 (40%)** |
| Routine messages wrongly sent to emergency (64) | 2 (3%) | 8 (12%) |
| **All 310 messages** | | |
| Emergencies caught (132) | 14 (11%) | 108 (82%) |
| Routine messages wrongly sent to emergency (140) | 5 (4%) | 8 (6%) |
| Questions about danger signs wrongly sent to emergency (22) | 4 (18%) | 1 (5%) |
| Same-day messages sent to emergency (28) | 0 | 0 |
| Newborn emergencies caught (10, not in scope) | 1 | 2 |
| **The walkthrough phrase "nina homa na kichwa kinauma sana"** | **missed** | caught |

By language, all batches, draft gate: English 85%, Swahili 85%, Sheng 53%.

**Read the v2 row.**
- The draft's 100% on v1 is overfitting.
- On wording it was never tuned on, the draft catches **40%** of emergencies. The live gate catches 5%.
- The draft is a large improvement. Pattern matching alone still cannot be the only safety net (see section 6).
- **New false alarms found in v2**, to fix with the four in section 3:
  - "will the nurse check if I am pale?" and "Wanaangalia kama nimepauka kliniki?"
  - "how do I stop malaria fever in pregnancy?" and "Nawezaje kuzuia homa ya malaria?"
  - "Mimba ya kwanza nilitokwa na damu nyingi baada ya kujifungua" (a past pregnancy)
  - "my gums bleed when I brush"
  - "which foods add blood?"
  - "Je, degedege linaweza kuzuiwa?"
- **Since 18 November:** the live AI prompt already carries a second safety net: *"If the participant describes any sign of physical distress or urgency, advise them to seek care promptly…"* (Decision 7).

Reproduce:

```
python -m ocs.eval.score_gate                                     # current gate on the corpus
python -m ocs.eval.score_gate --node ocs/eval/proposed_danger_gate.py
```

Held-out messages are in `ocs/eval/heldout.py`. Baseline report: `docs/eval/danger-gate-baseline.md`.

---

## 2. Clinical decisions needed from you

### 2.1 New ninth category: pallor (HB p14, BOP p39)

The draft adds a `pallor` category. It catches:
- "looking pale", and white palms, lips, eyes, nails, gums or tongue
- the anaemia symptoms from BOP p39: extreme tiredness, shortness of breath, racing heartbeat
- dizziness, but **only with** one of those other symptoms or a word like "all the time". "I felt dizzy once when I stood up fast" was a false alarm, so dizziness alone no longer triggers.
- a haemoglobin reading of 6.9 or below (BOP p40: "Below 7, severe, needs admission")

**Decision 1:** Should the BOP p39 anaemia symptoms (tiredness, breathlessness, dizziness, racing heart) go to the **emergency** path, the same as "looking pale"? The knowledge base says Zeya "should also catch" them, but it does not say how urgent they are. The alternative is a same-day facility visit, which the gate cannot do yet (see 2.5).

**Decision 2:** Is "dizzy only with another sign" right? Or should dizziness alone trigger?

### 2.2 Where some symptoms are filed

These are my proposals. The emergency reply is the same for every category, so the choice mainly changes the tags health workers see in reports.

| Symptom | Filed under | Source |
|---|---|---|
| Confusion | headache_vision (pre-eclampsia signs) | BOP p15, p16 |
| Blood pressure 160/110 or above, from a booklet reading | headache_vision | BOP p15 |
| Pain under the ribs | abdominal_pain | BOP p15, p16 |
| Haemoglobin below 7 | pallor | BOP p40 |
| Chills, foul-smelling discharge, constant pelvic pain | fever (infection signs) | BOP p46 |
| Fainting, collapse, not responding | convulsions | HB p14 |

**Decision 3:** Approve the filing, or name better categories.

### 2.3 Questions about danger signs (safety trade-off)

Today "what are the signs of bleeding I should watch for?" sends the mother an emergency alarm. The draft sends a message to the normal answer path when **both** of these are true:
- it reads as a general question ("what are the signs of…", "is … normal", "dalili za…", "ni kawaida…", or about a friend or sister), **and**
- it has no sign that the problem is happening to her now ("I have", "I'm", "my baby has", "nina", "naona", "nime-…" and similar).

A message that is a question and also says it is happening now still goes to emergency. For example, "I have bleeding, is it normal?" goes to emergency.

**The risk:** "is it normal to bleed at 30 weeks?" goes to the normal answer path, but the mother may in fact be bleeding.

**Decision 4:** Which do you prefer?

- **(a)** Keep the exemption. The normal answer is required to name the danger sign and tell her to go to the facility now if it is happening to her. That rule goes in the AI prompt in step 4.
- **(b)** Drop the exemption. Every match gets the emergency reply, and we accept false alarms on questions.
- **(c)** Keep the exemption, but send a short fixed line before the answer: "If this is happening to you now, go to the facility now", with the numbers. That line is written in advance, so no AI is involved.

My recommendation is **(c)**. It keeps the emergency path free of the AI and never leaves a mother without the facility message.

### 2.4 Newborn danger signs (HB p19, NG24 p661)

The knowledge base lists newborn danger signs: poor feeding, fast breathing, hot or cold, yellow eyes or palms, fits, and others. The gate has never covered them. It caught 2 of 8 newborn cases only by accident: "baby" plus "convulsions", and "Mtoto ana homa".

**Decision 5:** Should newborn signs become a tenth category in a later change? If yes, I'll draft those patterns separately for your review.

### 2.5 Same-day messages

The corpus has 24 SAME_DAY messages: vomiting with no fluids kept down, 41 weeks with no labour, BP 140–159/90–109, Hb 7–9.9, protein in urine, and low mood lasting more than two weeks after birth. The draft sends **none** of them to emergency, which is correct. The gate has only two routes, though, so the AI handles them.

**Decision 6:** Is it acceptable for the AI to handle same-day messages for now, with a prompt rule (step 4) that it must tell her to visit a facility today?

---

## 3. Swahili and Sheng patterns to approve

Every row needs your sign-off. Please check that each one is real usage in Migori, that none matches harmless everyday speech, and what common phrasings are missing.

"…" means up to about 20 characters of other words in between.

| # | Category | The draft matches | Example that triggers | Concern |
|---|---|---|---|---|
| S1 | bleeding | toka / tokwa (na) / ona / vuja + damu | "Natokwa na damu", "Nimeanza kutokwa damu" | |
| S2 | bleeding | damu + (ina/ime)toka, vuja, tiririka | "Damu inatoka" | |
| S3 | bleeding | damu kwenye…, damu ukeni | "Damu ukeni" | |
| S4 | headache_vision | kichwa … sana / mno / kali | "Kichwa kinauma sana" | **Confirmed false alarm:** "Kichwa kizuri sana" triggers. Needs a pain word. |
| S5 | headache_vision | kichwa … kinauma / kinaniuma … sana / mno / vibaya | "Kichwa kinaniuma vibaya" | Missed "kupita kiasi" in set B |
| S6 | headache_vision | maumivu makali ya kichwa | | |
| S7 | headache_vision | ukungu; giza machoni; naona giza / ukungu / nyota / vibaya; sioni vizuri | "Naona giza" | Missed "Macho yangu hayaoni vizuri" in set B |
| S8 | headache_vision | changanyikiwa | "Nimechanganyikiwa" | |
| S9 | headache_vision | Presha / BP 160 or more over anything, or anything over 110 or more | "Presha yangu ilikuwa 165/112" | Also English |
| S10 | pallor | …pauka | "Nimepauka" | |
| S11 | pallor | viganja / midomo / macho / kucha … vyeupe / meupe / myeupe / nyeupe | "Viganja vyangu ni vyeupe" | |
| S12 | pallor | mweupe, weupe | "Mimi ni mweupe sana" | **Broad**: "weupe" may be used for skin colour in general. Please check. |
| S13 | pallor | pumua kwa shida | "Napumua kwa shida" | |
| S14 | pallor | kizunguzungu … with moyo / pumua / mweupe / nimechoka / kila siku / kila mara / sana | "Nina kizunguzungu na moyo unadunda kwa kasi" | Decision 2 |
| S15 | pallor | moyo … unadunda / unapiga … kasi / haraka | | |
| S16 | fever | homa (any) | "Nina homa" | **Broad**: "homa" alone triggers. The live gate needs "homa kali". |
| S17 | fever | joto jingi / kali / sana; mwili … joto | "Mwili una joto kali" | |
| S18 | fever | …tetemeka | "Natetemeka" | Shaking can be cold or fear |
| S19 | fever | uchafu … unanuka / harufu; harufu mbaya | "Uchafu unanuka" | **Confirmed false alarm:** "harufu mbaya ya chakula" triggers. Needs discharge or uchafu nearby. |
| S20 | fetal_movement | mtoto … hachezi / hajacheza / hatembei / hasogei / hajasogea / amepunguza / ameacha | "Mtoto hajacheza leo" | **Confirmed false alarm:** "Mtoto ameacha kulia" triggers. Drop "ameacha" or require kucheza after it. |
| S21 | fetal_movement | sihisi / simhisi mtoto | | |
| S22 | fetal_movement | Sheng: hamove / hajamove | "Mtoto hajamove" | |
| S23 | abdominal_pain | tumbo … sana / mno / kali / vibaya | "Tumbo linauma sana" | **Confirmed false alarm:** "Tumbo kubwa sana" (big belly) triggers. Needs a pain word. |
| S24 | abdominal_pain | maumivu makali ya tumbo; maumivu … mbavu | | |
| S25 | water_breaking | maji … yametoka / yanatoka / yanavuja / yamevunjika / yamepasuka / yamekatika; maji … ya…toka | "Maji yananitoka" | |
| S26 | water_breaking | chupa … imepasuka / imevunjika / imetoboka | "Chupa imepasuka" | Please confirm "chupa" is used for waters breaking locally |
| S27 | convulsions | …zirai, amezimia, alizimia | "Alizirai" | |
| S28 | convulsions | anguka … tetemeka; poteza fahamu | "Alianguka akapoteza fahamu" | |
| S29 | swelling | uso / mikono / vidole / macho … umevimba / imevimba / vimevimba / yamevimba / kuvimba / umefura / imefura / vimefura / kufura | "Uso wangu umevimba" | |
| Q1 | question check | dalili za… | "Dalili za kutoka damu ni zipi?" | Exempts only general questions; see 2.3 |
| Q2 | question check | ni kawaida | "Ni kawaida kutokwa damu kidogo?" | |
| Q3 | question check | inaweza kumdhuru | | |
| N1 | happening now | nina, niko, natoka, naona, naumwa, nahisi, sihisi, simhisi, nimeona, nimeanza, any nime… or nili… word | | These keep the emergency route |

**The Swahili patterns already in the live gate stay as they are:** kutoka damu, damu nyingi, kichwa kuuma, macho kuona vibaya, homa kali, baridi mwilini, mtoto hatembei/hachezi, tumbo kuuma sana, maji yamekatika/yakutoka, degedege, kupoteza fahamu, kuvimba sana.

**Please add** any phrasing mothers in Migori use that is not listed, including Dholuo words. The gate has no Dholuo patterns today.

---

## 4. English patterns added (summary)

These are not clinical wording, but please check that nothing here is too broad.

| Category | Added | Watch for |
|---|---|---|
| bleeding | bleed / bleeding / spotting; "blood" except blood pressure, test, group, sugar, level, count, type, donor, transfusion, bank; losing or passing blood | **"blood" is broad.** "I want to donate blood" was a false alarm in set B. |
| headache_vision | bad / terrible / pounding headache; head + hurts + very / so / can't; blurry; flashes of light; fuzzy; double vision; confused | |
| pallor | look / am / feel pale; white palms or lips; breathless; heart racing; extremely tired; tired just walking; Hb 6.9 or below | |
| fever | fever / feverish; shivering; shaking; hot and cold; temperature 38–42; foul or smelly discharge; pelvic pain | "fever" alone triggers. The live gate needs "high fever". |
| fetal_movement | baby not moving or kicking, moves less; haven't felt or can't feel the baby; movements reduced; fewer kicks | |
| abdominal_pain | bad / sharp stomach pain; stomach + hurts + very / so / won't stop; pain under the ribs | |
| water_breaking | waters broke / burst; leaking water or fluid; wet + running down legs | |
| convulsions | plural convulsions / seizures; had a fit; unconscious; blacked out; collapsed; jerking; not answering or responding | |
| swelling | face / hands / fingers / eyes + swollen / puffy / puffed; swelled up | |

The draft also fixes the gaps logged in `docs/ocs-migration.md`: "blurry", plural convulsions and seizures, and "stopped moving" and "passed out" now match.

---

## 5. Corpus labels to approve

The full corpus is in `ocs/eval/corpus.py`. Each message has a label and a knowledge base section. **All labels and all Swahili text are my drafts.** Please check these judgement calls first:

1. **E027–E031**, anaemia symptoms labelled EMERGENCY (see Decision 1).
2. **E051–E052**, confusion labelled EMERGENCY.
3. **E087–E089**, severe booklet readings labelled EMERGENCY. **S016–S022**, moderate readings labelled SAME_DAY. Boundaries are BP 160/110 (BOP p15) and Hb 7 (BOP p40).
4. **S001–S007**, vomiting with no fluids kept down labelled SAME_DAY, not EMERGENCY.
5. **S008–S011**, low mood lasting more than two weeks after birth labelled SAME_DAY.
6. **R001–R012**, the 12 questions about danger signs labelled ROUTINE (see Decision 4).
7. **E098–E100**, mixed English and Swahili messages ("Natoka blood kidogo, is it okay?") labelled EMERGENCY.

---

## 6. Limits I could not resolve

- **Four confirmed Swahili false alarms** (rows S4, S19, S20, S23). I left them unfixed so you can choose the wording. Each needs a pain or discharge word near it.

- **Held-out recall is about 50%.** Set B misses included:
  - "red discharge", "bright red on the toilet paper"
  - "worst headache of my life", "seeing flashes"
  - "I am burning up", "my body is very hot", "sharp cramps that won't go away"
  - "the baby is quiet today", "I haven't felt any movement"
  - "soaked with water"
  - "shaking on the floor", "foaming at the mouth"
  - "kupita kiasi", "hayaoni vizuri"

  New patterns will always trail new wording. I recommend a second safety net on the **normal** path: a rule in the AI prompt that any danger sign must get the facility message and numbers (step 4). The emergency path itself stays free of the AI. **Decision 7:** approve this approach.
- **The test messages are written, not real.** None comes from a real mother. Real Zeya messages, anonymised and with your permission, would be a much better test.
- **The Swahili is not checked.** I am not a fluent Migori Swahili speaker. Every Swahili pattern and test message needs a native speaker's review.
- **No Dholuo.** No Dholuo patterns or test messages exist.
- **Typos and spelling variants** are barely tested ("bleding", "hedache", "damuu").
- **The question check is English-heavy.** It has only three Swahili question forms.
- **Reduced movement:** "Fewer than 10 movements in a day" (NG12 p173) is marked pending in the knowledge base. No pattern counts movements.

---

## 7. What happens after your sign-off

1. Apply your changes to the draft.
2. Write the approved patterns into both `backend/app/services/danger_signs.py` and `ocs/nodes/danger_gate.py` in the same change, and update the parity tests so the two files stay identical.
3. Re-run the corpus and a **new** held-out set, then report the before and after numbers.
4. Open a pull request. Nothing is deployed until it is merged and you have seen the final numbers.

Sign-off: ______________________ Date: __________
