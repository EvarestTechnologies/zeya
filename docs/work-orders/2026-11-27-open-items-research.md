# Claude.ai brief: close the open items for Zeya release 1

Paste everything below the line into a new Claude.ai chat with Research turned on. Upload these files to the same chat first.

**From the repository, branch `feat/guideline-alignment` (PR #62)**
1. `docs/review/clinical-signoff.md`
2. `docs/review/danger-gate.md`
3. `docs/review/kiswahili-starter.md`
4. `docs/review/system-prompt.md`
5. `docs/zeya-knowledge-base.md`
6. `docs/clinical/moh-knowledge-base.md`
7. `docs/clinical/gaps.md`
8. `ocs/nodes/emergency_response.py`
9. `ocs/nodes/danger_question_line.py`

**From `~/Downloads`**
10. `Mother-Child-Health-Handbook-MOH-NEW-LAYOUT-10th-Sep-2020.pdf` (HB)
11. `NATIONAL GUIDELINES ON QUALITY OBSTETRICS AND PERINATAL CARE_ August 2024.pdf` (NG24)
12. `Basic Obstetric Protocol_Shareable.pdf` (BOP)

When Claude.ai replies, paste the whole reply back to Claude Code. Each answer has an ID, so it can be applied directly.

---

I am Stella Oiro, a licensed clinical officer and the clinical reviewer for Zeya. Zeya is a WhatsApp antenatal education service for pregnant women in Kenya, in English and Kiswahili. Release 1 is used with synthetic test participants only. The files attached are the current sign-off sheet, the review files, the runtime content and the three Ministry of Health documents (HB, NG24 and BOP), which are Zeya's only clinical sources.

Claude Code has built release 1 from my sign-off. It had to guess in the places below. Research each one so nothing is guessed. Rules:
- Use only the attached Ministry documents for clinical content. Use primary sources (government, county, Meta, Kenya Red Cross) for everything else.
- Cite every answer with a document and page, or a URL.
- Mark anything you cannot confirm as **UNVERIFIED**, and say what would confirm it. Never fill a gap from general knowledge.
- Give exact replacement text, not advice. Claude Code will paste it as written.

## Items

**K1. Kiswahili wording.** Check every Kiswahili string below for natural Kenyan Kiswahili that a mother in Migori would understand, keeping the English meaning exactly:
- the five Kiswahili entries in `docs/zeya-knowledge-base.md`
- the Kiswahili fixed line in `ocs/nodes/danger_question_line.py`
- the Kiswahili emergency reply in `ocs/nodes/emergency_response.py`
- the Kiswahili fixed reply in section C2 of the sign-off sheet
- the Kiswahili welcome phrase in section C3 ("kulingana na nyaraka za Wizara ya Afya ya Kenya")

Check these terms in particular: "mwandani" (birth companion), "kituo cha afya", "foliki asidi", "chandarua kilichowekwa dawa cha muda mrefu", "Msalaba Mwekundu Kenya", "mhudumu wa afya" against "mtoa huduma wa afya", and "Chanzo: Kitabu cha Afya ya Mama na Mtoto, Wizara ya Afya". Where the Kiswahili edition of the MCH Handbook or another MOH Kiswahili publication uses a term, prefer that term and cite it.

**K2. How mothers write danger signs.** For each of the nine HB p14 danger signs, list the ways pregnant women in Kenya actually write them in English, Kiswahili and Sheng on WhatsApp or SMS, including common misspellings. Use published sources only: Jacaranda Health PROMPTS papers, MomConnect, Beshte, Kenyan mHealth studies, or Kiswahili health glossaries. Give each phrasing with its source. Do not write regex. Claude Code will turn approved phrasings into patterns for my sign-off. Start with the set C misses in section 0 of `docs/review/danger-gate.md`.

**K3. Emergency numbers.** For each number, find an official source and say what it is, who runs it, whether it is free and staffed 24 hours, and the date of the source:
- 999 and 112
- 922 (reported as a national ambulance line launched 5 August 2026)
- 1199 and 1514 (both reported for Kenya Red Cross). Which is the ambulance line, and is either retired?
- the Migori County emergency ambulance dispatch numbers 0740 587 479, 0740 588 519 and 0740 588 853 (county poster), and +254 724 024 296

Then give the exact English and Kiswahili lines for the emergency reply, listing only numbers with an official source. I will call each number myself before ticking it.

**K4. Human escalation line.** Meta's WhatsApp Business Messaging Policy requires automated chats to offer a clear path to a human. Quote the current policy text with its URL and date. Then draft the escalation line for the fixed "I do not have reviewed information…" reply, in English and Kiswahili, using only numbers confirmed in K3. Under 30 words each.

**K5. Test labels that lost their source.** The page check removed two rules, and four test labels relied on them (`docs/clinical/gaps.md`). Quote the exact text of:
- NG24 p52 to p55 on nausea and vomiting, for S005 and S006 (vomiting that starts at 30 to 32 weeks)
- NG24 p289 to p291 on low mood and depression after birth, for S008 and S010 (low mood for three weeks, not said to be worsening)

For each label, say whether the guideline supports SAME_DAY, ROUTINE or EMERGENCY, or is silent. Quote the sentence; do not decide for me.

**K6. System prompt within 120 words.** Two existing tests block the approved prompt in `docs/review/system-prompt.md`: a 120-word limit, not counting placeholders, and a required sentence saying the rules are guidance and an output guard checks the reply. Write a version of 120 words or fewer that keeps every rule of the approved prompt and all of these:
- the exact fallback sentence
- the words "drug" and "name" on the same line
- the word "distress"
- "{participant_data.language_preference}"
- "{temp_state.kb_section}" and "{temp_state.llm_context}", once each
- the guard sentence

Show the word count. If it cannot be done without losing a rule, say which rule and why.

**K7. Permission letter.** Draft a short letter from Evarest Technologies to the Division of Reproductive, Maternal, Newborn, Child and Adolescent Health, Ministry of Health Kenya, asking permission to adapt wording from the MCH Handbook (2020) and NG24 for a free, non-commercial pilot education chatbot. List the exact passages used: the five entries in `docs/zeya-knowledge-base.md` and the danger signs on HB p14. Find the Division's current postal and email address from an official source, or mark it UNVERIFIED.

## Reply format

Reply with one section per item, using these exact headings so Claude Code can apply them:

```
### K1
For each string:
- File:
- Current:
- Corrected:
- Source:
- Status: VERIFIED or UNVERIFIED

### K2
For each danger sign: a table with columns Phrasing | Language (en, sw, sheng, mixed) | Source

### K3
A table with columns Number | Service | Operator | Free | 24 hours | Source and date | Status
Then the exact English and Kiswahili emergency reply lines.

### K4
The policy quote with URL and date, then the English and Kiswahili escalation lines.

### K5
For each label: ID | Guideline quote with page | What it supports

### K6
The full prompt text, then the word count, then any rule that could not fit.

### K7
The letter text, then the address with source or UNVERIFIED.
```

Finish with a list of everything still UNVERIFIED, and what would confirm it.
