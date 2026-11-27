# Answers to the open items for Zeya release 1 (K1 to K7)

Prepared 27 November 2026 for Stella Oiro, clinical reviewer. Answers `docs/work-orders/2026-11-27-open-items-research.md` on PR #62 (commit 62a1e6c).

Clinical text comes only from HB (MCH Handbook 2020), NG24 (national guidelines, August 2024) and BOP (Basic Obstetric Protocols 2026). Page numbers are printed page numbers. Everything else cites a URL. UNVERIFIED means no primary source confirmed it.

## Read this first

1. **The Migori number in the live reply has no source.** `+254 724 024 296` appears in `emergency_response.py` and `danger_question_line.py`. It is not on the county poster and was not found on any county or government page. The poster lists `0740 587 479`, `0740 588 519` and `0740 588 853`. Use a poster number, or keep +254 724 024 296 only if Stella can name where it comes from. See K3.
2. **B3 row 10 was wrong, and the error was in the earlier page check, not Claude Code's work.** NG24 p52 says vomiting that starts late in pregnancy needs a clinician to look for other causes. The page check said NG24 did not say this. See K5.
3. **The live emergency reply sends her to a different place in each language.** The English says "nearest health facility". The Kiswahili says "hospitali" (hospital). K1 fixes it.
4. **The earlier word count for the approved prompt was wrong.** It was given as 125 words. Claude Code counted about 170, and Claude Code is right. K6 has a version of exactly 120 words that passes every prompt test.

---

### K1

The handbook is the only Ministry source with any Kiswahili. Its cover reads: "Beba kitabu hiki kila mara uendapo kliniki na uonyeshe muhudumu wa afya" ("Carry this handbook at all times during a visit to the health facility and show it to the health worker"). The title is "AFYA YA MAMA NA MTOTO" (HB cover, printed edition June 2020; also in the [technet-21 copy of the handbook](https://technet-21.org/media/com_resources/hbr/9194/ken-hbr-2020.pdf)). NG24 and BOP contain no Kiswahili clinical terms. Every other Kiswahili choice below is a fluent-speaker judgement and stays UNVERIFIED until a native Migori speaker and Stella approve it.

**Term rulings**

| Term | Ruling | Source | Status |
|---|---|---|---|
| mhudumu wa afya / mtoa huduma wa afya | Use **muhudumu wa afya**, the handbook's own term and spelling. Drop "mtoa huduma wa afya". | HB cover | VERIFIED |
| Kitabu cha Afya ya Mama na Mtoto | Keep. The handbook calls itself "kitabu hiki", and its Kiswahili title is "Afya ya Mama na Mtoto". | HB cover | VERIFIED |
| kliniki | Use for the antenatal visit, as the handbook does. | HB cover | VERIFIED |
| kituo cha afya | Keep for "health facility" in danger-sign and emergency text. In Kenya it can also mean a level 3 health centre. That is acceptable, because both kinds of facility can help her. | none in HB, NG24 or BOP | UNVERIFIED |
| mwandani | Replace with **mtu wa kukusindikiza** (someone to accompany you). "Mwandani" means a close friend or confidant, not a birth companion. | none | UNVERIFIED |
| foliki asidi | Replace with **asidi ya foliki**, and keep "(IFAS)" so it matches the clinic's label. | none | UNVERIFIED |
| chandarua kilichowekwa dawa cha muda mrefu | Change to **chandarua chenye dawa cha muda mrefu**, which is shorter and the usual phrasing. | none | UNVERIFIED |
| Msalaba Mwekundu Kenya | Write **Kenya Red Cross** in the Kiswahili text too. The legal name in Cap. 256 is English. The Kiswahili form "Msalaba Mwekundu la Kenya" appears only in secondary sources. | [Kenya Red Cross Society Act, Cap. 256](https://new.kenyalaw.org/akn/ke/act/1965/29/eng@2022-12-31) | VERIFIED for the English name |
| Chanzo: Kitabu cha Afya ya Mama na Mtoto, Wizara ya Afya | Keep. | HB cover | VERIFIED |

**Strings**

- File: `docs/zeya-knowledge-base.md`, anc_visits (sw)
- Current: "Nenda kliniki ya ujauzito kwa mara ya kwanza mapema iwezekanavyo, na uhudhurie mara 8 wakati wa ujauzito wako. Beba Kitabu chako cha Afya ya Mama na Mtoto kila unapoenda kliniki na umwonyeshe mhudumu wa afya."
- Corrected: "Nenda kliniki ya wajawazito mapema iwezekanavyo, na uhudhurie mara 8 katika kipindi cha ujauzito wako. Beba Kitabu cha Afya ya Mama na Mtoto kila mara uendapo kliniki na uonyeshe muhudumu wa afya."
- Source: second sentence is the HB cover wording. First sentence follows HB p13.
- Status: second sentence VERIFIED. First sentence UNVERIFIED.

- File: `docs/zeya-knowledge-base.md`, danger_signs (sw)
- Current: "…mtoto kucheza kidogo au kutocheza, maji kutoka (chupa kupasuka), na degedege au kifafa. Ukiwa na dalili yoyote kati ya hizi, nenda kituo cha afya sasa hivi."
- Corrected: "Dalili za hatari wakati wa ujauzito: maumivu makali ya kichwa, kuonekana kupauka, kutokwa na damu ukeni, homa, maumivu makali ya tumbo, kuvimba uso na mikono, mtoto tumboni kucheza kidogo au kutocheza kabisa, maji kutoka ukeni (chupa kupasuka), na degedege au kifafa. Ukiwa na dalili yoyote kati ya hizi, nenda kituo cha afya sasa hivi."
- Source: HB p14 (English list). "Mtoto tumboni" carries HB's "unborn baby". "Ukeni" makes clear where the water comes from.
- Status: UNVERIFIED. Stella should confirm whether "chupa kupasuka" is what Migori mothers say.

- File: `docs/zeya-knowledge-base.md`, daily_care (sw)
- Current: "…Meza vidonge vya madini ya chuma na foliki asidi kila siku katika kipindi chote cha ujauzito. … Lala ndani ya chandarua kilichowekwa dawa cha muda mrefu. …"
- Corrected: "Kula mlo mmoja wa ziada kila siku. Kunywa maji mengi, angalau glasi 8 kwa siku. Meza vidonge vya madini ya chuma na asidi ya foliki (IFAS) kila siku katika kipindi chote cha ujauzito. Epuka kazi nzito na upumzike zaidi. Lala ndani ya chandarua chenye dawa cha muda mrefu. Fanya mazoezi mepesi mara kwa mara."
- Source: HB p13.
- Status: UNVERIFIED. The output guard test for B4 matches only the English phrase, so check that the guard lets the Kiswahili sentence through.

- File: `docs/zeya-knowledge-base.md`, food_groups (sw)
- Current: as in the file.
- Corrected: no change.
- Source: HB p18.
- Status: UNVERIFIED (reads naturally).

- File: `docs/zeya-knowledge-base.md`, birth_plan (sw)
- Current: "Panga mpango wa kujifungua pamoja na mhudumu wako wa afya: … mwandani wako wakati wa kujifungua, usafiri na mchangiaji damu. Mwenzi wako anaweza kusaidia kwa kupanga usafiri, pesa, mwandani wa kujifungua na vifaa vya dharura."
- Corrected: "Andaa mpango wa kujifungua pamoja na muhudumu wa afya: tarehe inayotarajiwa ya kujifungua, kituo cha afya utakapojifungulia, atakayekuhudumia, nambari ya simu ya kituo, mtu wa kukusindikiza wakati wa kujifungua, usafiri, na mtu wa kuchangia damu. Mwenzi wako anaweza kusaidia kwa kupanga usafiri, pesa, mtu wa kukusindikiza na vifaa vya dharura."
- Source: HB inside cover and HB p3. "Panga mpango" is redundant, so it becomes "Andaa mpango".
- Status: UNVERIFIED.

- File: `ocs/nodes/danger_question_line.py` (sw)
- Current: "Kama hili linakutokea sasa, nenda kituo cha afya sasa hivi. Nambari za dharura: 999 au 112, ambulensi ya kitaifa 922, Msalaba Mwekundu Kenya 1199 au 1514, huduma ya dharura ya Kaunti ya Migori +254 724 024 296."
- Corrected: "Kama hili linakutokea sasa, nenda kituo cha afya sasa hivi. Kwa dharura piga 922 bila malipo, au 999 au 112. Ambulensi ya Kenya Red Cross: 1514. Ambulensi ya Kaunti ya Migori: 0740 587 479."
- Source: numbers per K3.
- Status: wording UNVERIFIED. Numbers as in K3.

- File: `ocs/nodes/emergency_response.py` (sw)
- Current header: "1. Nenda hospitali iliyo karibu nawe mara moja au piga simu ya dharura. … 3. USISUBIRI kuona kama dalili zitaboreshwa zenyewe."
- Corrected header: "DHARURA: Hii inaweza kuwa dalili ya hatari inayohitaji matibabu ya haraka. Fanya yafuatayo sasa hivi:\n\n1. Nenda kituo cha afya kilicho karibu nawe mara moja, au piga simu ya dharura.\n2. Ikiwa huwezi kusafiri, mwombe mtu aliye karibu akusaidie kufika kituo cha afya.\n3. USISUBIRI kuona kama dalili zitapungua zenyewe.\n\n"
- Corrected footer: "\n\nHii ni taarifa ya kielimu, si utambuzi wa ugonjwa. Kwa ushauri, wasiliana na muhudumu wa afya."
- Source: "kituo cha afya" matches the English "health facility". "Zitaboreshwa" (will be improved) is replaced by "zitapungua" (will ease). "Muhudumu wa afya" follows the HB cover.
- Status: UNVERIFIED.

- File: `docs/review/clinical-signoff.md`, C2 (sw)
- Current: "Sina taarifa iliyokaguliwa kujibu swali hilo. Tafadhali uliza mtoa huduma wako wa afya."
- Corrected: "Sina taarifa iliyokaguliwa ya kujibu swali hilo. Tafadhali muulize muhudumu wa afya."
- Source: HB cover term.
- Status: UNVERIFIED.

- File: `docs/review/clinical-signoff.md`, C3 (sw)
- Current: "kulingana na nyaraka za Wizara ya Afya ya Kenya"
- Corrected: "kulingana na machapisho ya Wizara ya Afya ya Kenya"
- Source: none. "Nyaraka" reads as official records. "Machapisho" (publications) is closer to "materials".
- Status: UNVERIFIED.

### K2

**No published source quotes Kenyan mothers' own messages for any danger sign.** The PROMPTS work confirms that mothers write in English, Kiswahili and Sheng. [NPR reported in September 2026](https://www.npr.org/2026/09/17/nx-s1-5962840/artificial-intelligence-ai-chatbot-pregnancy-maternal-health) that PROMPTS "understands messages in English, Swahili and Sheng". The [AAAI TRIM-AI paper](https://ojs.aaai.org/index.php/AAAI/article/view/26709/26481) describes "code-mixed SMS messages (between English and Swahili)". Its full text was blocked, so no example messages could be extracted. The phrasings below are the only ones found. Most come from health writers, not from mothers.

| Danger sign | Phrasing | Language | Source |
|---|---|---|---|
| Severe headache | "Kuumwa na kichwa" / "Kichwa inaweza uma" | sw (Kenyan spoken, clinic talk) | [Machakos Level 5 Hospital family planning discourse study](https://www.academia.edu/108821451/Language_Management_in_Family_Planning_Discourses_at_Machakos_Level_5_Hospital_Kenya) |
| Severe headache (BP link) | "presha" for high blood pressure | sw | [Rough Guide Swahili phrasebook](https://mis.piass.ac.rw/librarian/applctDoc/904_20%20The%20Rough%20Guide%20Swahili%20Phrasebook.pdf) |
| Vaginal bleeding | "kutokwa damu ukeni" | sw (Tanzanian health site) | [ULY Clinic](https://www.ulyclinic.com/addo1/maumivu-ya-tumbo-kwenye-ujauzito) |
| Vaginal bleeding | "kuvuja damu" | sw (health worker course) | [OpenLearn Create, Swahili HEAT module 21](https://www.open.edu/openlearncreate/mod/oucontent/view.php?id=53411&printable=1) |
| Fever | "joto jingi mwilini" | sw (health worker course) | [OpenLearn Create, module 20](https://www.open.edu/openlearncreate/mod/oucontent/view.php?id=53410&printable=1) |
| Fever | "kutetemeka" (shaking) | sw | [ULY Clinic](https://www.ulyclinic.com/addo1/jinsi-ya-kufahamu-kama-utoaji-mimba-kwa-dawa-umefanikiwa) |
| Breaking water | "maji kutoka ukeni" | sw | [ULY Clinic](https://www.ulyclinic.com/addo1/maumivu-ya-tumbo-kwenye-ujauzito) |
| Convulsions (related) | "kuzimia" (fainting) | sw | [ULY Clinic](https://www.ulyclinic.com/addo1/maumivu-ya-tumbo-kwenye-ujauzito) |
| Infection (related) | "uchafu unaonuka ukeni" | sw | [ULY Clinic](https://www.ulyclinic.com/elimu-kwa-mjamzito-magonjwa/dalili-za-hatari-wakati-wa-ujauzito) |

**Set C misses.** No published source was found for any of them: "im bleading", "my waters brok", "my hed is paining", "worst headache of my life", "I am burning up", "soaked with water", "foaming at the mouth", "Bebi hachezi siku nzima", "Maji imevunja", "Ako na fits". All are UNVERIFIED.

**What would confirm real phrasings**
1. **The AI-NEO trial dataset.** The trial ran in Ahero and Kisumu, built an urgency detector for Swahili and Luo SMS, and its registry entry says individual data "will be available at end of the project by contacting the study team" ([NCT05369806](https://clinicaltrials.gov/study/NCT05369806)). Its sites are next to Migori, and it covers Dholuo.
2. **A short phrasing session.** Stella runs it with community health promoters and mothers in Migori, records the wording they use, and signs it off as clinical reviewer.
3. **A data-sharing request to Jacaranda Health.** Ask for de-identified PROMPTS danger-sign messages.

### K3

| Number | Service | Operator | Free | 24 hours | Source and date | Status |
|---|---|---|---|---|---|---|
| 922 | SHA 922 Lifeline, national medical emergency and ambulance dispatch | Social Health Authority, National Ambulance Dispatch Centre | Yes. The government article says "Calls to 922 will be free on every network." | Yes. The Standard describes the dispatch centre as "a 24-hour command centre at SHA headquarters in Nairobi". | [gaa.go.ke, 11 Aug 2026](https://www.gaa.go.ke/node/4419); launched 5 Aug 2026, per [AllAfrica](https://allafrica.com/stories/202608060070.html) | VERIFIED (government source for free calls; 24-hour status from the press) |
| 999 | National emergency line | National Police Service | Toll-free, per press reports | Not stated by NPS | [NPS Customer Service Charter](https://nationalpolice.go.ke/sites/default/files/2025-01/NPS%20Customer%20Service%20Charter.pdf): "Hotline: 999/112/911" | VERIFIED as an NPS hotline. Free and 24 hours are UNVERIFIED from NPS itself |
| 112 | National emergency line | National Police Service | Toll-free, per press reports | Not stated by NPS | Same NPS charter | Same as 999 |
| 1514 | E-Plus ambulance | Emergency Plus Medical Services, owned by Kenya Red Cross | Yes. E-Plus's page says "Call us toll-free on: 1514 or 0700 395 395/0738 395 395". | Not stated on that page | E-Plus Facebook page as mirrored by [govserv.org](https://www.govserv.org/KE/Nairobi/117600501609745/E-Plus-Kenya), posts dated August 2026 | VERIFIED as E-Plus's current ambulance line (mirror of the operator's own page) |
| 1199 | Kenya Red Cross toll-free hotline. Formerly the E-Plus ambulance line. | Kenya Red Cross Society | Yes, per older sources | Not stated | KRCS listed as "Toll Free: 1199" by [LifeLine International](https://lifeline-international.com/?p=3351); E-Plus once listed 1199 too | UNVERIFIED as a current ambulance line. E-Plus now advertises 1514, so 1199 may be the general Red Cross line |
| 0740 587 479, 0740 588 519, 0740 588 853 | Migori County Emergency Ambulance Dispatch, "for maternal, newborn and medical emergencies" | Migori County Government, County Emergency Dispatch Team | Not stated. These are ordinary mobile numbers, so airtime applies. | Poster says "Call the dispatch team anytime" | County poster PDF supplied by Stella (made in Word, 6 Oct 2026). Not found on [migori.go.ke](https://migori.go.ke/departments/public-health-and-medical-services). | UNVERIFIED online. The poster is the only source. |
| +254 724 024 296 | Shown in the live reply as "Migori County emergency dispatch" | Unknown | Unknown | Unknown | None found. It is not on the poster. | UNVERIFIED. Do not show it without a source. |

The emergency reply should carry four numbers at most. A mother in an emergency needs one number to call, not six.

**English emergency reply lines**
```
Emergency numbers (free from any phone):
- Ambulance: 922
- Emergency services: 999 or 112
- Kenya Red Cross ambulance: 1514
- Migori County ambulance: 0740 587 479
```

**Kiswahili emergency reply lines (DRAFT)**
```
Nambari za dharura (bila malipo kutoka simu yoyote):
- Ambulensi: 922
- Huduma za dharura: 999 au 112
- Ambulensi ya Kenya Red Cross: 1514
- Ambulensi ya Kaunti ya Migori: 0740 587 479
```

The Migori line is an ordinary mobile number, so it is not free. Write the header as "free from any phone" only if all the listed numbers are free. Otherwise remove "(free from any phone)" from the header and write "922 (free)". Before ticking, Stella calls all four and confirms that 922 and 1514 answer from Migori on a Safaricom line and an Airtel line.

### K4

**Policy text.** Meta's WhatsApp Business Messaging Policy, last updated 23 September 2026, at [whatsappbusiness.com/policy](https://whatsappbusiness.com/policy/). Businesses may use automation, "but must also have available prompt, clear, and direct escalation paths."

The policy expects a path to a person at the business that runs the chat. None of the K3 numbers is a line for health questions: 922, 999, 112 and the dispatch lines are for emergencies only. The lines below point her to a health worker. They do not fully meet Meta's rule, because the person she reaches does not work for Zeya. To meet the rule, Evarest needs a staffed contact for Zeya, such as a support line answered during working hours. That is a decision for Evarest, and no number exists for it yet.

**English (24 words)**
> To talk to a person, visit your nearest health facility or ask your community health promoter. In an emergency, call 922, free from any phone.

**Kiswahili DRAFT (24 words)**
> Ili kuzungumza na mtu, tembelea kituo cha afya kilicho karibu nawe au muulize muhudumu wa afya ya jamii. Kwa dharura, piga 922 bila malipo.

Status: wording UNVERIFIED. The 922 facts come from K3.

### K5

| ID | Guideline quote with page | What it supports |
|---|---|---|
| S005, S006 (vomiting that starts at 30 to 32 weeks) | NG24 p52: "Nausea and vomiting of pregnancy nearly always begins before 9 weeks of gestation; symptoms presenting later in pregnancy should prompt the clinician to consider other causes." Also p52: "The onset of symptoms is usually early in the first trimester at around 4-6 weeks gestation and peaks at 9 weeks gestation. Vomiting abates in 90 % of cases by 20 weeks." | The guideline supports a clinician assessment when vomiting starts late. It does not give a time frame, so it does not choose between SAME_DAY and ROUTINE. It does not support EMERGENCY. |
| S005, S006 (if she cannot keep fluids down) | NG24 p53: "Women who cannot tolerate oral liquids for a prolonged period or who have clinical signs of dehydration should receive intravenous hydration including dextrose and vitamins." NG24 p54: "Management as in-patient is recommended if: … There is evidence of dehydration and the patient is ketotic." | This applies only if the test message says she cannot keep fluids down. Then the guideline supports clinician care and possible admission, without a time frame. |
| S008, S010 (low mood for three weeks after birth, not said to be worsening) | NG24 p291: "Postpartum blues are transient in nature with an onset after the third postpartum day… Symptoms typically peak by day five and resolve by day ten postpartum." Also p291: "Careful monitoring for a worsening or prolongation of symptoms." NG24 p289: "For women with suspected post- natal depression, the Edinburgh Postnatal Depression Scale can be used for screening purposes prior to referral to a psychiatrist for further evaluation and management." | Three weeks is beyond the day-ten end of the blues. So these messages count as "prolongation", and the guideline supports screening for postnatal depression. It gives no time frame. Silent on SAME_DAY versus ROUTINE. Does not support EMERGENCY. |

**Correction to B3 row 10.** The removed knowledge base sentence ("go to the clinic if nausea first starts late in pregnancy") has a source after all: NG24 p52, quoted above. Stella can reinstate it with that citation, worded as "Tell your health worker if vomiting starts late in pregnancy". That is Stella's decision.

### K6

```
Use only the Kenya Ministry of Health entries below.
If not covered, reply exactly: "I do not have reviewed information to answer that question. Please ask your healthcare provider."
Never diagnose, dose, name unlisted drugs, give weight gain numbers, advise on vitamin A or salt, or say all mothers get malaria tablets.
Never give phone numbers or links.
For severe headache, pallor, bleeding, fever, severe belly pain, swollen face or hands, less baby movement, waters breaking or fits, say: go to a health facility now.
For other worries or distress, say: visit a health facility today.
End with the entry's source.
Reply under 120 words, plainly, in her stored language ({participant_data.language_preference}).
Rules are guidance; an output guard checks replies.

{temp_state.kb_section}

{temp_state.llm_context}
```

**Word count: 120**, using the test's own method (placeholders removed, split on whitespace).

**Test conditions.** It was checked against every condition in `ocs/tests/test_grounded_prompt.py` and `ocs/tests/test_pipeline_structure.py`, and all of them pass:
- ≤120 words.
- Both placeholders appear exactly once.
- `{participant_data.language_preference}` is present.
- "diagnose" appears only on a line with "never".
- No 9-digit numbers.
- "reviewed information" and "healthcare provider" are present.
- "output" and "guard" are present.
- "stored language" is present.
- "drug" and "name" are on the same line.
- "link" appears only on a line with "never".
- "distress" is present.
- The exact fallback sentence is present.

**What changed from the approved prompt**
1. **"You are Zeya, a pregnancy education assistant for women in Kenya" is gone.** It gives the model its role, but it is not one of the safety rules. If Stella wants it back, swap "plainly," for "as Zeya, a pregnancy educator," at a cost of two words over the limit. That needs either one more cut or a test limit of 125.
2. **"Looking pale" became "pallor", and "the baby moving less" became "less baby movement".** These are instructions to the model, so it still matches her own words.
3. **"A medicine the entries do not name" became "unlisted drugs".** The meaning is the same.
4. **"Short, plain sentences" became "plainly".**

No rule was dropped.

### K7

**Letter**

> Evarest Technologies Ltd
> Pioneer House, Block 4/1136, Oginga Odinga Street
> P.O. Box 40100, 40100 Kisumu, Kenya
>
> 27 November 2026
>
> The Head
> Division of Reproductive, Maternal, Newborn, Child and Adolescent Health
> Ministry of Health
> Afya House, Cathedral Road
> P.O. Box 30016–00100, Nairobi
>
> Dear Sir or Madam,
>
> **Request for permission to adapt wording from the Mother and Child Health Handbook (2020) and the National Guidelines on Quality Obstetrics and Perinatal Care (2024)**
>
> Evarest Technologies is developing Zeya, a free WhatsApp education service for pregnant women in Kenya, in English and Kiswahili. Zeya is a non-commercial pilot. It is not yet used with real participants, and no participant will be enrolled before ethics approval, a NACOSTI licence and registration with the Office of the Data Protection Commissioner.
>
> Zeya speaks only from Ministry of Health materials. A licensed clinical officer reviews every message, and each message names the Ministry document it comes from. We request the Ministry's permission to reproduce and lightly adapt the following passages, with full acknowledgement.
>
> From the Mother and Child Health Handbook (MOH 216, 2020):
> 1. Cover: carry the handbook to every visit and show it to the health worker.
> 2. Page 13, Care during pregnancy: one extra meal a day, at least 5 of the 10 food groups, at least 8 glasses of water, daily iron and folic acid supplements, rest and avoiding heavy work, sleeping under a long-lasting insecticidal net, attending antenatal care 8 times, and regular gentle exercise.
> 3. Page 14, Danger signs in pregnancy: the nine signs and the advice to seek skilled care at the health facility.
> 4. Page 18: the 10 food groups.
> 5. Inside cover and page 3: the items of the birth plan, and how the partner can help.
>
> From the National Guidelines on Quality Obstetrics and Perinatal Care (2024):
> 6. Page 107: the topics taught at each antenatal contact. These are used only as internal context, to choose which approved Handbook message suits a woman's stage of pregnancy. They are not sent to women word for word.
>
> Zeya states that it is not an official Ministry of Health product. We would welcome any conditions the Ministry wishes to set, including a review of our Kiswahili wording, and we will share the final message set with the Division before any launch.
>
> Yours faithfully,
>
> Stella Oiro
> Chief Executive Officer, Evarest Technologies Ltd
> Licensed Clinical Officer

**Address and source**
- **Division name.** "The Division of Reproductive Maternal Newborn Child and Adolescent Health (DRMNCAH)", with enquiries to "Ministry of Health, P. O. Box 30016 – 00100 Nairobi, Kenya". Source: [Kenya EWENE Acceleration Plan 2026–2028, Ministry of Health, 2026](https://www.afro.who.int/sites/default/files/2026-06/EWENE%20Kenya%202026-2028.pdf). VERIFIED.
- **Email.** comms.rmncah@health.go.ke, from the same plan ([alternate copy](https://afro.who.int/sites/default/files/2026-06/EWENE%20Kenya%20Plan%202026%20-%202028.pdf)). VERIFIED.
- **Street address.** "Afya House, Cathedral Road". Source: [health.go.ke/node/939](https://health.go.ke/node/939). VERIFIED.
- **Name of the current Head of Division.** UNVERIFIED. That is why the letter is addressed to "The Head".

---

## Still UNVERIFIED, and what would confirm it

1. **Every Kiswahili string except the handbook cover terms.** A native Kenyan Kiswahili speaker from Migori, then Stella's sign-off.
2. **"Chupa kupasuka" as local usage.** Stella, or community health promoters in Migori.
3. **Real phrasings for all nine danger signs, and all set C misses.** The AI-NEO dataset (NCT05369806), a Migori phrasing session, or Jacaranda data.
4. **Whether 999 and 112 are free and answered 24 hours.** A National Police Service statement, or the Communications Authority numbering plan.
5. **Whether 1199 still reaches an ambulance.** Calling 1199 from Migori, or the current redcross.or.ke contact page. That page could not be fetched from here.
6. **Whether 1514 is answered 24 hours.** Calling it, or eplus.co.ke. That site could not be fetched from here.
7. **The three Migori poster numbers.** A copy on migori.go.ke or a county social media account, plus Stella's calls. Also whether they take calls from any network.
8. **+254 724 024 296.** Stella names its source, or it comes out of the reply.
9. **A Zeya-staffed escalation contact that meets Meta's rule.** An Evarest decision and a working number.
10. **The name of the current Head of DRMNCAH.** A call to the Ministry switchboard or the Division's email.
11. **The Kiswahili name of Kenya Red Cross.** The redcross.or.ke site, or the Society's logo artwork.
