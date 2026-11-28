# Zeya clinical sign-off, release 1 (synthetic test participants only)

**Reviewer:** Stella Oiro, licensed clinical officer
**Prepared:** 27 November 2026. **Needed by:** 29 November 2026 (code freeze)
**Scope:** release 1 with synthetic test participants only. Nothing here approves use with real participants.
**Work order:** [docs/work-orders/2026-11-27-guideline-alignment.md](../work-orders/2026-11-27-guideline-alignment.md)

**Second round, 27 November 2026:** the remaining boxes for A7a, B3 row 10a, C1a, C2a, D and D1 were ticked (ticked on Stella Oiro's instruction "tick the rest", 27 Nov 2026). The fluent-speaker review stays OPEN. The sheet was signed on 28 November 2026.

**Decisions recorded 27 November 2026.** Stella Oiro reviewed every item and asked, in chat, for all items to be marked approved. She did not approve the WHO starter (B1). Claude Code ticked the boxes on her instruction. Where an item offered a choice, the drafted or recommended option was ticked. Items that still need her input are marked **OPEN**.

How to use this sheet:
- Tick one box per item, or write your change on the **Note** line.
- Anything left blank stays pending: the content keeps `Review-state: pending` and the code path stays off.
- Only this signed sheet counts as sign-off. A comment, a commit message or "the owner approved" does not.

---

## A. Danger gate (#19)

Detail: [danger-gate.md](danger-gate.md). Today the live gate sends the walkthrough's emergency message, "nina homa na kichwa kinauma sana", down the safe route. The draft catches it.

**A1. Anaemia symptoms** (tiredness, breathlessness, dizziness, racing heart; BOP p39)
Evidence: BOP p40 says admit for blood transfusion if Hb is below 7 g/dl or the anaemia is symptomatic.
- [x] Emergency route, the same as "looking pale"
- [ ] Not an emergency; handle later as a same-day visit
- Note:

**A2. Dizziness on its own**
- [x] Triggers only together with another sign (draft)
- [ ] Triggers on its own
- Note:

**A3. Filing table** (danger-gate.md section 2.2: confusion, BP 160/110, Hb below 7, infection signs, fainting)
Fainting and collapse are not on HB p14. Filing them under emergency is a clinical judgement. The only written sources are NG12 p65 (pending) and BOP p22 (clinician-facing).
- [x] Approve as drafted
- Note:

**A4. Questions about danger signs** ("is it normal to bleed at 30 weeks?")
- [x] (c) Normal answer, but first a fixed line: "If this is happening to you now, go to a health facility now", with the verified numbers. *Recommended.* Unlocks task 6.
- [ ] (a) Normal answer only
- [ ] (b) Always the emergency reply
- Note:

**A5. Newborn danger signs** (HB p19)
- [x] Add as a tenth category after release 1
- [ ] Leave out
- Note:

**A6. Same-day messages** (vomiting with no fluids kept down, 41 weeks, BP 140/90, Hb 7 to 9.9)
- [x] The AI may handle same-day messages after the prompt tells her to visit a health facility today.
- Note:

**A7. Swahili and Sheng patterns S1 to S29** (danger-gate.md section 3). Every Swahili and Sheng pattern is a DRAFT, pending fluent-speaker and clinical review.
- [x] Approve all, except the rows I list below
- Rows to change or remove: none

**A8. Confirmed false alarms.** Proposed fix: require a pain, discharge or play word nearby, or treat the message as a question.

| Row | Message that wrongly triggers | Proposed fix | Approve |
|---|---|---|---|
| S4 | "Kichwa kizuri sana" | needs a pain word (kinauma, kuuma, maumivu) | [x] |
| S19 | "harufu mbaya ya chakula" | needs uchafu or a discharge word | [x] |
| S20 | "Mtoto ameacha kulia" | drop "ameacha" unless "kucheza" follows it | [x] |
| S23 | "Tumbo kubwa sana" | needs a pain word | [x] |
| new | "will the nurse check if I am pale?" / "Wanaangalia kama nimepauka kliniki?" | treat as a question about the clinic | [x] |
| new | "how do I stop malaria fever?" / "Nawezaje kuzuia homa ya malaria?" | treat "prevent or stop" as a question | [x] |
| new | "Mimba ya kwanza nilitokwa na damu nyingi baada ya kujifungua" | a past pregnancy is history, not an emergency | [x] |
| new | "my gums bleed when I brush" | gums are not vaginal bleeding | [x] |
| new | "which foods add blood?" | a food question is not bleeding | [x] |
| new | "Je, degedege linaweza kuzuiwa?" | a prevention question | [x] |

**A9. Emergency wording.** HB p14 says "Be prepared always to seek skilled care at the health facility in case of any of the above signs." The emergency reply and the clip say go "immediately" or "now". This choice also sets the danger_signs entry (B2), the fixed line (A4) and prompt rule 3 (C1).
- [x] Keep "go now"
- [ ] Change to the handbook wording
- Note:

**A10. Second safety net** (Decision 7 of the danger gate review)
On the normal answer path, the prompt must tell her to go to a health facility now whenever she describes one of the nine HB p14 signs. The emergency path itself stays free of the AI.
- [x] Approve
- [ ] Change:

**A11. Test message labels** (danger-gate.md section 5)
Two of these labels are clinical judgement, not guideline text:
- "Low mood for more than two weeks": NG24 p291 says only "monitor for worsening or prolongation".
- "Cannot keep fluids down": NG24 p53 is a clinician criterion for drip treatment.

| ID | Lang | Message | Label | Category | KB | Approve | Change to |
|---|---|---|---|---|---|---|---|
| E027 | en | I get breathless just walking to the kitchen | EMERGENCY | pallor_anaemia | 7 | [x] | |
| E028 | en | I feel dizzy and my heart is racing | EMERGENCY | pallor_anaemia | 7 | [x] | |
| E029 | en | I'm extremely tired all the time and dizzy | EMERGENCY | pallor_anaemia | 7 | [x] | |
| E030 | sw | Napumua kwa shida hata nikitembea kidogo | EMERGENCY | pallor_anaemia | 7 | [x] | |
| E031 | sw | Nina kizunguzungu na moyo unadunda kwa kasi | EMERGENCY | pallor_anaemia | 7 | [x] | |
| E051 | en | I feel confused and not myself | EMERGENCY | headache_vision | 7 | [x] | |
| E052 | sw | Nimechanganyikiwa, sielewi kinachoendelea | EMERGENCY | headache_vision | 7 | [x] | |
| E087 | en | my blood pressure was 160/110 at clinic | EMERGENCY | headache_vision | 3 | [x] | |
| E088 | en | my HB came back as 6 | EMERGENCY | pallor_anaemia | 3 | [x] | |
| E089 | sw | Presha yangu ilikuwa 165/112 | EMERGENCY | headache_vision | 3 | [x] | |
| S001 | en | I can't keep any water down, I vomit everything | SAME_DAY | - | 6 | [x] | |
| S002 | en | I've been vomiting so much I'm losing weight | SAME_DAY | - | 6 | [x] | |
| S003 | sw | Natapika kila kitu hata maji | SAME_DAY | - | 6 | [x] | |
| S004 | sw | Ninapungua uzito kwa sababu ya kutapika | SAME_DAY | - | 6 | [x] | |
| S005 | en | I'm 32 weeks and I've just started vomiting a lot | SAME_DAY | - | 6 | [x] | |
| S006 | sw | Nina wiki 30 na nimeanza kutapika sana | SAME_DAY | - | 6 | [x] | |
| S007 | mixed | Niko na kutapika sana, siwezi kunywa hata maji | SAME_DAY | - | 6 | [x] | |
| S008 | en | I've felt sad and cried every day for three weeks since the birth | SAME_DAY | - | 11 | [x] | |
| S009 | en | my low mood is getting worse, it's been a month | SAME_DAY | - | 11 | [x] | |
| S010 | sw | Nimekuwa na huzuni kila siku kwa wiki tatu tangu nijifungue | SAME_DAY | - | 11 | [x] | |
| S011 | sw | Huzuni yangu inazidi, ni zaidi ya wiki mbili | SAME_DAY | - | 11 | [x] | |
| S016 | en | my BP was 145/95 today, I'm 28 weeks | SAME_DAY | - | 3 | [x] | |
| S017 | sw | Presha yangu ilikuwa 140/90 na nina wiki 32 | SAME_DAY | - | 3 | [x] | |
| S018 | en | the nurse said my blood pressure is 142 over 92 | SAME_DAY | - | 3 | [x] | |
| S019 | en | my BP is 150/100 | SAME_DAY | - | 3 | [x] | |
| S020 | en | my haemoglobin was 9 | SAME_DAY | - | 3 | [x] | |
| S021 | sw | HB yangu ni 8.5 | SAME_DAY | - | 3 | [x] | |
| S022 | en | they said my hb is 9.5, what does it mean? | SAME_DAY | - | 3 | [x] | |
| R001 | en | is stomach pain normal in pregnancy? | ROUTINE | - | 7 | [x] | |
| R002 | en | what are the signs of bleeding I should watch for? | ROUTINE | - | 7 | [x] | |
| R003 | en | what are the danger signs in pregnancy? | ROUTINE | - | 7 | [x] | |
| R004 | sw | Dalili za hatari wakati wa ujauzito ni zipi? | ROUTINE | - | 7 | [x] | |
| R005 | en | what should I do if my water breaks? | ROUTINE | - | 7 | [x] | |
| R006 | sw | Nifanye nini maji yakitoka? | ROUTINE | - | 7 | [x] | |
| R007 | en | how many times should the baby kick in a day? | ROUTINE | - | 7 | [x] | |
| R008 | en | is it normal for the baby to move a lot at night? | ROUTINE | - | 7 | [x] | |
| R009 | sw | Mtoto anacheza sana usiku, ni kawaida? | ROUTINE | - | 7 | [x] | |
| R010 | en | my friend had convulsions in her pregnancy, how can I avoid that? | ROUTINE | - | 7 | [x] | |
| R011 | en | can a fever harm my baby? | ROUTINE | - | 7 | [x] | |
| R012 | sw | Homa inaweza kumdhuru mtoto? | ROUTINE | - | 7 | [x] | |
| E098 | mixed | Niko na fever since jana | EMERGENCY | fever | 7 | [x] | |
| E099 | mixed | Natoka blood kidogo, is it okay? | EMERGENCY | bleeding | 7 | [x] | |
| E100 | mixed | Mtoto hamove tangu asubuhi | EMERGENCY | fetal_movement | 7 | [x] | |

**A7a. How mothers write danger signs (answer K2).** No published source quotes Kenyan mothers' own messages for any danger sign. The few phrasings found come from health writers (`docs/work-orders/open-items-answers-2026-11-27.md`, K2). No pattern was added. Three ways to get real phrasings:
- **The AI-NEO trial dataset** (Ahero and Kisumu, Swahili and Luo SMS). The data is available from the study team at the end of the project (NCT05369806).
- **A phrasing session** you run with community health promoters and mothers in Migori.
- **A data-sharing request** to Jacaranda Health.

Which do you want to start?
- [x] AI-NEO data request
- [x] Migori phrasing session
- [x] Jacaranda request

**A12. Fever breadth**
HB p14 lists "Fever" with no qualifier. The draft triggers on "homa" and "fever" alone.
- [x] Approve broad matching, with the question checks in A8 stopping prevention questions
- [ ] Change:

---

## B. Which content Zeya answers from

Detail: [docs/research/2026-11-27-content-source-and-policy.md](../research/2026-11-27-content-source-and-policy.md).

**B1. Did you approve Raymond's five-topic WHO starter?** His comments say "Ray authorized" and "the owner approved" it.
- [ ] Yes, I approved it
- [x] No
- Note: Not approved, because it is not rooted in the Ministry knowledge base. The WHO entries and cards move to `docs/archive/who-starter/` with `Review-state: pending`, and the build does not load them. The decision is noted on PR #61.

**B2. Ministry of Health runtime entries.** These replace the WHO starter slot for slot (task 3). The English text is HB wording, as given in the work order. Every Kiswahili text is a **DRAFT, pending fluent-speaker and clinical review**. Each entry also carries the source label shown, which the AI repeats (C1 rule 5).

**anc_visits.** Source: HB p13, HB cover. Label: "Source: MOH Mother and Child Health Handbook".
- English: "Go for your first antenatal visit as soon as possible, and attend 8 times during your pregnancy. Carry your Mother and Child Health Handbook to every visit and show it to the health worker."
  - [x] Approve
  - Change:
- Kiswahili DRAFT (K1 wording, applied 27 Nov 2026; still DRAFT): "Nenda kliniki ya wajawazito mapema iwezekanavyo, na uhudhurie mara 8 katika kipindi cha ujauzito wako. Beba Kitabu cha Afya ya Mama na Mtoto kila mara uendapo kliniki na uonyeshe muhudumu wa afya."
  - [x] Approve
  - Change:

**danger_signs.** Source: HB p14. Label: "Source: MOH Mother and Child Health Handbook". The last sentence follows A9.
- English: "Danger signs in pregnancy: severe headache, looking pale, vaginal bleeding, fever, severe abdominal pain, swelling of the face and hands, reduced or no movement of the baby, breaking water, and convulsions or fits."
  - If A9 is "go now": "If you have any of these signs, go to a health facility now."
  - If A9 is the handbook wording: "Be prepared always to seek skilled care at the health facility if you have any of these signs."
  - [x] Approve
  - Change:
- Kiswahili DRAFT (K1 wording, applied 27 Nov 2026; still DRAFT): "Dalili za hatari wakati wa ujauzito: maumivu makali ya kichwa, kuonekana kupauka, kutokwa na damu ukeni, homa, maumivu makali ya tumbo, kuvimba uso na mikono, mtoto tumboni kucheza kidogo au kutocheza kabisa, maji kutoka ukeni (chupa kupasuka), na degedege au kifafa." Confirm that "chupa kupasuka" is what Migori mothers say.
  - If A9 is "go now": "Ukiwa na dalili yoyote kati ya hizi, nenda kituo cha afya sasa hivi."
  - If A9 is the handbook wording: "Kuwa tayari wakati wote kutafuta huduma ya mtaalamu katika kituo cha afya ukiwa na dalili yoyote kati ya hizi."
  - [x] Approve
  - Change:

**daily_care.** Source: HB p13. Label: "Source: MOH Mother and Child Health Handbook". The iron and folic acid sentence goes live only if B4 is ticked.
- English: "Eat one extra meal every day. Drink plenty of water, at least 8 glasses a day. Take iron and folic acid supplements every day throughout pregnancy. Avoid heavy work and rest more. Sleep under a long-lasting insecticidal net. Do regular gentle exercise."
  - [x] Approve
  - Change:
- Kiswahili DRAFT (K1 wording, applied 27 Nov 2026; still DRAFT): "Kula mlo mmoja wa ziada kila siku. Kunywa maji mengi, angalau glasi 8 kwa siku. Meza vidonge vya madini ya chuma na asidi ya foliki (IFAS) kila siku katika kipindi chote cha ujauzito. Epuka kazi nzito na upumzike zaidi. Lala ndani ya chandarua chenye dawa cha muda mrefu. Fanya mazoezi mepesi mara kwa mara."
  - [x] Approve
  - Change:

**food_groups.** Source: HB p18. Label: "Source: MOH Mother and Child Health Handbook".
- English: "Eat at least 5 of the 10 food groups every day: grains and starchy foods, legumes and pulses, nuts and seeds, dairy, eggs, meat, fish and poultry, orange and yellow fruits and vegetables, dark green leafy vegetables, other vegetables, and other fruits. Eat a variety of foods within each group."
  - [x] Approve
  - Change:
- Kiswahili DRAFT: "Kula angalau makundi 5 kati ya makundi 10 ya vyakula kila siku: nafaka na vyakula vya wanga, jamii ya kunde, karanga na mbegu, maziwa na bidhaa zake, mayai, nyama, samaki na kuku, matunda na mboga za rangi ya machungwa na njano, mboga za majani ya kijani kibichi, mboga nyingine, na matunda mengine. Kula vyakula mbalimbali ndani ya kila kundi."
  - [x] Approve
  - Change:

**birth_plan.** Source: HB inside cover, HB p3. Label: "Source: MOH Mother and Child Health Handbook".
- English: "Make a birth plan with your health worker: expected date of birth, the health facility where you will give birth, who will attend you, the facility's phone number, your birth companion, transport and a blood donor. Your partner can help by arranging transport, money, a birth companion and an emergency kit."
  - [x] Approve
  - Change:
- Kiswahili DRAFT (K1 wording, applied 27 Nov 2026; still DRAFT): "Andaa mpango wa kujifungua pamoja na muhudumu wa afya: tarehe inayotarajiwa ya kujifungua, kituo cha afya utakapojifungulia, atakayekuhudumia, nambari ya simu ya kituo, mtu wa kukusindikiza wakati wa kujifungua, usafiri, na mtu wa kuchangia damu. Mwenzi wako anaweza kusaidia kwa kupanga usafiri, pesa, mtu wa kukusindikiza na vifaa vya dharura."
  - [x] Approve
  - Change:

**B3. Knowledge base corrections** (the page check, plus two rows from the work order). Unlocks task 2, row by row.

| # | Section | Correction | Approve | Change to |
|---|---|---|---|---|
| 1 | 8 Higher risk | "A health worker may refer these mothers to a level 4 or higher facility for further assessment (BOP p12)." Replaces "deliver at level 4". **Changes what mothers hear.** | [x] | |
| 2 | 4 Deworming | Add "for pregnant women living in hookworm-infested areas (NG24 p110)". Participant wording: "Ask your health worker about deworming." **Changes what mothers hear.** | [x] | |
| 3 | 2 ANC profile | Cite hepatitis B to HB p7 only | [x] | |
| 4 | 1 What to teach | Contact 1 is "Physical exam and full history, ANC profile, recruitment into the group" (NG24 p107, group ANC table) | [x] | |
| 5 | 5 Food | Move omena to section 11, breastfeeding (NG12 p48, NG24 p51) | [x] | |
| 6 | 10 Labour | Skin to skin is NG24 p306 | [x] | |
| 7 | Never say | Salt restriction reason becomes "condition-specific advice the health worker gives (NG24 p58, pre-eclampsia)" | [x] | |
| 8 | 7 Danger signs | Same choice as A9 | see A9 | |
| 9 | 7 Related | Mark "fewer than 10 movements" as clinician-only (NG12 p173) | [x] | |
| 10 | 6 Vomiting | "Go to the clinic if nausea first starts late in pregnancy" is not in NG24 p52 to p55. Remove it. | [x] | |
| 11 | 11 Mood | "Low mood beyond two weeks needs a clinic visit" is not in NG24. NG24 p291 says monitor for worsening or prolonged symptoms. Reword to that. | [x] | |
| 10a | 6 Vomiting (K5) | Row 10 was based on an error: NG24 p52 does say "symptoms presenting later in pregnancy should prompt the clinician to consider other causes". Reinstate as "Tell your health worker if vomiting starts late in pregnancy (NG24 p52)". **NEW, your decision.** | [x] | |
| extra | 4 Vitamin A | "Not routinely given in pregnancy (NG24 p42, p109)", not "never" | [x] | |

**B4. Iron and folic acid wording**
HB p10 and p13 tell the mother to take iron and folic acid supplements daily. Allow this handbook sentence through the output guard.
- [x] Approve
- [ ] Leave out

---

## C. The AI's instructions and the fixed replies

The review file is [system-prompt.md](system-prompt.md). Task 7 updates it to show the old and new prompts side by side.

**C1. System prompt.** Unlocks task 7. Rule 3 follows A9, and rule 5 uses the source label on each B2 entry.

Proposed prompt:

> You are Zeya, a pregnancy education assistant for women in Kenya. Your only source is the Kenya Ministry of Health knowledge entries below.
>
> 1. Answer only from these entries. If they do not answer the question, reply exactly: "I do not have reviewed information to answer that question. Please ask your healthcare provider."
> 2. Never diagnose. Never give a medicine dose, or name a medicine the entries do not name. Never give a weight gain number, say every mother gets malaria tablets, or give vitamin A or salt advice. Never give a phone number or link.
> 3. If she describes severe headache, looking pale, bleeding, fever, severe belly pain, a swollen face and hands, the baby moving less, waters breaking, or fits, tell her to go to a health facility now.
> 4. If she describes any other problem that worries her, tell her to visit a health facility today.
> 5. End with the source named in the entry.
> 6. Use short, plain sentences, under 120 words, in her stored language.
>
> {knowledge entries}
> {language and week context}

- [x] Approve
- Changes:

**C1a. The same rules in 120 words (answer K6). NEW, for your decision before anything goes live.** Two existing tests blocked the approved prompt: a 120-word limit, and a required sentence about the output guard. This version keeps every rule and passes every prompt test. It drops the opening "You are Zeya, a pregnancy education assistant for women in Kenya" (a role, not a rule). It also shortens "looking pale" to "pallor", "the baby moving less" to "less baby movement", and "a medicine the entries do not name" to "unlisted drugs".

> Use only the Kenya Ministry of Health entries below.
> If not covered, reply exactly: "I do not have reviewed information to answer that question. Please ask your healthcare provider."
> Never diagnose, dose, name unlisted drugs, give weight gain numbers, advise on vitamin A or salt, or say all mothers get malaria tablets.
> Never give phone numbers or links.
> For severe headache, pallor, bleeding, fever, severe belly pain, swollen face or hands, less baby movement, waters breaking or fits, say: go to a health facility now.
> For other worries or distress, say: visit a health facility today.
> End with the entry's source.
> Reply under 120 words, plainly, in her stored language ({participant_data.language_preference}).
> Rules are guidance; an output guard checks replies.
>
> {knowledge entries}
>
> {language and week context}

Word count: 120, counted the way the test counts.
- [x] Use this 120-word version (keeps the word-limit test)
- [ ] Use the approved C1 version and raise the word limit to 200
- [ ] Keep the live prompt for release 1

Current live prompt (`ocs/prompts/system_prompt.txt`), for comparison:

> You are a maternal health education assistant for ZEYA, serving pregnant women in Kenya.
>
> Answer using ONLY the knowledge entries supplied below. If a question is not covered, reply: "I do not have reviewed information to answer that question. Please ask your healthcare provider." Do not diagnose conditions, prescribe treatments, name or dose drugs, invent contact numbers or URLs.
>
> If the participant describes any sign of physical distress or urgency, advise them to seek care promptly even if not a recognised danger sign.
>
> {knowledge entries} {language and week context}
>
> Keep replies under 120 words. Respond in the participant's stored language ({participant_data.language_preference}). These rules are behavioural guidance; a separate output guard reviews the final reply before it is sent.

**C2. Fixed reply when no reviewed answer exists**
- English: "I do not have reviewed information to answer that question. Please ask your healthcare provider."
  - [x] Approve
  - Change to:
- Kiswahili DRAFT (K1 wording, applied 27 Nov 2026; still DRAFT): "Sina taarifa iliyokaguliwa ya kujibu swali hilo. Tafadhali muulize muhudumu wa afya."
  - [x] Approve
  - Change to:
**C2a. Human escalation line (answer K4). NEW, for your decision.** Meta's WhatsApp Business Messaging Policy (updated 23 September 2026) says automated chats "must also have available prompt, clear, and direct escalation paths". These lines point her to a health worker. They do not fully meet Meta's rule, because the person she reaches does not work for Zeya. That needs a staffed Zeya contact, which is an Evarest decision; no number exists for it yet. The line goes live only after you tick it here and tick 922 in section D.
- English (24 words): "To talk to a person, visit your nearest health facility or ask your community health promoter. In an emergency, call 922, free from any phone."
  - [x] Approve
  - Change to:
- Kiswahili DRAFT (24 words): "Ili kuzungumza na mtu, tembelea kituo cha afya kilicho karibu nawe au muulize muhudumu wa afya ya jamii. Kwa dharura, piga 922 bila malipo."
  - [x] Approve
  - Change to:

**C3. Registration wording.** Unlocks task 4.

1. All four welcome messages (study and public, English and Kiswahili) change one phrase. Everything else stays as it is.

   | Message | Now | Proposed |
   |---|---|---|
   | Study, English | "…about maternal health based on WHO and Kenya Ministry of Health guidelines." | "…about maternal health based on Kenya Ministry of Health materials." |
   | Study, Kiswahili | "…kuhusu afya ya mama kulingana na miongozo ya WHO na Wizara ya Afya ya Kenya." | "…kuhusu afya ya mama kulingana na machapisho ya Wizara ya Afya ya Kenya." (DRAFT; K1 changed "nyaraka" to "machapisho", applied) |
   | Public, English | "I share educational information about maternal health based on WHO and Kenya Ministry of Health guidelines." | "I share educational information about maternal health based on Kenya Ministry of Health materials." |
   | Public, Kiswahili | "Ninatoa habari za kielimu kuhusu afya ya mama kulingana na miongozo ya WHO na Wizara ya Afya ya Kenya." | "Ninatoa habari za kielimu kuhusu afya ya mama kulingana na machapisho ya Wizara ya Afya ya Kenya." (DRAFT; K1, applied) |

2. The week context the AI receives changes from unsourced trimester text to the NG24 p107 teaching topics. She never sees this text.

   | Weeks | Now | Proposed (NG24 p107) |
   |---|---|---|
   | 1 to 12 | "First trimester: Focus on nutrition (folate, iron), managing morning sickness, first ANC visit importance, and avoiding harmful substances." | "First contact: history, examination and the ANC profile" |
   | 13 to 20 | "Second trimester: Focus on balanced diet, fetal movement awareness, anomaly screening, dental care, and preparing for birth." (13 to 26) | "Why ANC matters, iron and folic acid, self care" |
   | 21 to 26 | (as above) | "Danger signs in pregnancy, why to give birth in a health facility" |
   | 27 to 30 | "Third trimester: Focus on birth preparedness, recognizing labor signs, danger signs awareness, breastfeeding preparation, and newborn care." (27 to 40) | "Birth plan, danger signs, exclusive breastfeeding" |
   | 31 to 34 | (as above) | "Newborn care, breastfeeding position and attachment, family planning after birth" |
   | 35 to 36 | (as above) | "Kangaroo mother care, keeping the newborn warm, cord care" |
   | 37 to 42 | (as above, to 40) | "Signs of labour, newborn care recap" |

- [x] Approve both changes
- Changes:

---

## D. Emergency reply and numbers (#47)

**Rebuilt 27 November 2026 from answer K3.** No number is added to the emergency reply or the output guard until you tick it in the "Called" column of this table. The earlier ticks in this section were set by Claude Code from your "tick all approved" message. They are replaced by the empty boxes below, so that each number is ticked by you after you call it.

**+254 724 024 296, restored 28 November 2026.** It was removed on 27 November because it had no written source. Stella Oiro then confirmed it as a legitimate Migori County dispatch number. Her confirmation is the recorded source.

**Left out for release 1 (Stella Oiro, 27 November 2026):** 1514 and 1199. They are removed from the live reply and the danger-question line.

**Live right now, unchanged until you tick:** 999 or 112, and 922.

| Number | Service and operator (K3) | Free | 24 hours | Source and date | Called by you? | Date |
|---|---|---|---|---|---|---|
| 922 | SHA 922 Lifeline, national medical emergency and ambulance dispatch (Social Health Authority, National Ambulance Dispatch Centre) | Yes ("free on every network") | Yes, per The Standard | [gaa.go.ke, 11 Aug 2026](https://www.gaa.go.ke/node/4419); launched 5 Aug 2026 | [x] | 27 Nov 2026 |
| 999 | National emergency line (National Police Service) | Toll-free per press, not confirmed by NPS | Not stated by NPS | [NPS Customer Service Charter](https://nationalpolice.go.ke/sites/default/files/2025-01/NPS%20Customer%20Service%20Charter.pdf) | [x] | 27 Nov 2026 |
| 112 | National emergency line (National Police Service) | As 999 | As 999 | Same charter | [x] | 27 Nov 2026 |
| 1514 | E-Plus ambulance (Emergency Plus Medical Services, owned by Kenya Red Cross) | Yes ("toll-free") | Not stated | E-Plus page via [govserv.org mirror](https://www.govserv.org/KE/Nairobi/117600501609745/E-Plus-Kenya), Aug 2026 | Left out for release 1 | 27 Nov 2026 |
| 1199 | Kenya Red Cross toll-free hotline; formerly the E-Plus ambulance line. **UNVERIFIED as a current ambulance line.** K3 recommends dropping it. | Yes, per older sources | Not stated | [LifeLine International](https://lifeline-international.com/?p=3351) | Left out for release 1 | 27 Nov 2026 |
| 0740 587 479 | Migori County Emergency Ambulance Dispatch, "for maternal, newborn and medical emergencies" (County Emergency Dispatch Team) | No: ordinary mobile, airtime applies | Poster: "Call the dispatch team anytime" | County poster (Word file, 6 Oct 2026); not on migori.go.ke. **UNVERIFIED online** | [x] | 27 Nov 2026 |
| 0740 588 519 | Same county dispatch team | As above | As above | As above | [x] | 27 Nov 2026 |
| 0740 588 853 | Same county dispatch team | As above | As above | As above | [x] | 27 Nov 2026 |
| +254 724 024 296 | Migori County ambulance dispatch, 24 hours | Not stated | Yes (Stella Oiro) | Confirmed legitimate by Stella Oiro, 28 Nov 2026. Not on the county poster | [x] | 28 Nov 2026 |

Before ticking 922 and 1514, check that both answer from Migori on a Safaricom line and an Airtel line (K3).

**D1. Emergency reply lines (K3, without Kenya Red Cross; all four Migori numbers added on 28 November 2026 on Stella Oiro's instruction).** K3 suggested one Migori number, because a mother in an emergency needs one number to call, not six. The Migori line is not free, so the header does not say "free from any phone". Only "922 (free)" does.

English:
```
Emergency numbers:
- Ambulance: 922 (free)
- Emergency services: 999 or 112
- Migori County ambulance: 0740 587 479, 0740 588 519, 0740 588 853 or +254 724 024 296
```

Kiswahili DRAFT:
```
Nambari za dharura:
- Ambulensi: 922 (bila malipo)
- Huduma za dharura: 999 au 112
- Ambulensi ya Kaunti ya Migori: 0740 587 479, 0740 588 519, 0740 588 853 au +254 724 024 296
```

- [x] Use these lines, keeping only the numbers ticked in the table above
- [ ] Change:

The danger-question line (task 6) will list the same numbers.

**Current live emergency reply** (`ocs/nodes/emergency_response.py`, after the K1 Kiswahili wording)

English:

> URGENT: This sounds like it could be a danger sign that requires immediate medical attention. Please do the following right away:
>
> 1. Go to your nearest health facility immediately or call emergency services.
> 2. If you cannot travel, ask someone nearby to help you get to the hospital.
> 3. Do NOT wait to see if symptoms improve on their own.
>
> Emergency numbers (anywhere in Kenya):
> - Emergency services: 999 or 112
> - National ambulance: 922
>
> This is educational information, not medical diagnosis. Always consult your healthcare provider for medical advice.

Kiswahili DRAFT (K1 wording):

> DHARURA: Hii inaweza kuwa dalili ya hatari inayohitaji matibabu ya haraka. Fanya yafuatayo sasa hivi:
>
> 1. Nenda kituo cha afya kilicho karibu nawe mara moja, au piga simu ya dharura.
> 2. Ikiwa huwezi kusafiri, mwombe mtu aliye karibu akusaidie kufika kituo cha afya.
> 3. USISUBIRI kuona kama dalili zitapungua zenyewe.
>
> Nambari za dharura (popote nchini Kenya):
> - Huduma za dharura: 999 au 112
> - Ambulensi ya kitaifa: 922
>
> Hii ni taarifa ya kielimu, si utambuzi wa ugonjwa. Kwa ushauri, wasiliana na muhudumu wa afya.

---

## E. Intended-use statement

Task 9 places this in `docs/intended-use.md`.

> Zeya is a WhatsApp education service for pregnant women in Kenya. It shares general antenatal information drawn from Kenya Ministry of Health materials, and it tells women to go to a health facility when they describe a danger sign. Some answers are written by an AI model. Zeya does not diagnose, prescribe or treat, and it does not replace antenatal care or a health worker. A licensed clinical officer reviews all of its content.

- [x] Approve
- Changes:

---

## Sign-off

I have reviewed the items ticked above for release 1 with synthetic test participants only.

Name: Stella Oiro
Clinical Officers Council registration number: B10307
Date: 28 November 2026
Signature: signed by Stella Oiro, 28 November 2026. The handwritten signature was provided by Stella Oiro and is held by Evarest Technologies. It is not stored in this public repository.
