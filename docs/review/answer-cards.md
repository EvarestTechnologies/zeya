# Answer cards — review record

**Status: PENDING CLINICAL AND LANGUAGE REVIEW. Not approved for public use.**

This document lists every answer card in `docs/answer-cards.yaml` for review before
any card is set to `"review_status": "approved"`. No card may be shown to participants
until a clinician (preferably Achar or Kenya MoH-aligned reviewer) explicitly approves
it and a language reviewer approves any translated text.

---

## Scope and limitations

These five cards cover general antenatal education only, ported verbatim from the
five-entry WHO-linked starter KB (`knowledge-base-draft.md`, v0.1). They do not
provide diagnoses, prescriptions, drug doses, symptom assessments, emergency guidance
or facility-specific information.

**Swahili / Sheng translations:** No translated cards exist in v0. The trigger strings
and answers are English only. Kiswahili translations require a separate fluent-speaker
and clinical review before `language: sw` cards can be added. This is explicitly a
follow-up work item and is not silently fulfilled here.

**Original ~60-card ambition:** Issue #23 originally described approximately sixty
cards covering ANC contacts, discomforts, danger signs and newborn care. These five
cards are the agreed limited v0 starter scope (see execution-contract.md). The full
coverage remains a visible follow-up requirement.

**Matching accuracy:** The matcher uses word-overlap (Jaccard similarity) with light
suffix stemming and English stopword removal. It does not use AI or external tools.
Limitations: near-synonyms without shared word stems may miss; short questions
(<2 content tokens) fall below the token guard; typos reduce but do not eliminate
overlap; no Swahili matching in v0.

---

## Cards pending review

### 1 · `anc_purpose_en`

| Field | Value |
|-------|-------|
| ID | `anc_purpose_en` |
| KB ref | `anc_purpose` |
| Language | English |
| Review status | **pending** |
| Source | WHO starter KB v0.1 — anc_purpose entry |

**Triggers (English):**
- "Why should I go to ANC?"
- "What are pregnancy clinic visits for?"
- "Why should I attend antenatal care?"
- "What are antenatal visits for?"
- "What is the purpose of antenatal clinic visits when pregnant?"
- "Why should I attend antenatal care visits?"
- "Why do I need to attend antenatal visits?"

**Answer (English):**
> Antenatal visits provide health care, information, advice and emotional support
> during pregnancy. Contact a health worker after confirming your pregnancy, and
> attend the visits they recommend.

Reviewer action needed:
- [ ] Verify wording is accurate and appropriate for the Kenyan context.
- [ ] Confirm the answer does not imply a specific visit schedule.
- [ ] Approve or revise; set `review_status: approved` only after explicit sign-off.

---

### 2 · `pregnancy_records_en`

| Field | Value |
|-------|-------|
| ID | `pregnancy_records_en` |
| KB ref | `pregnancy_records` |
| Language | English |
| Review status | **pending** |
| Source | WHO starter KB v0.1 — pregnancy_records entry |

**Triggers (English):**
- "Should I keep my pregnancy health records?"
- "Why keep a record of pregnancy care?"
- "Should I keep records of my pregnancy care?"
- "Why is it important to keep my pregnancy health records?"
- "Why should I keep records of my pregnancy health care?"
- "How should I manage my maternity health records?"

**Answer (English):**
> Keep a record of your pregnancy health care and vaccines at home. Ask your health
> worker to explain information in your records that you do not understand.

Reviewer action needed:
- [ ] Confirm the guidance is consistent with Kenya MoH mother and child health (MCH)
  booklet practice.
- [ ] Approve or revise.

---

### 3 · `food_variety_en`

| Field | Value |
|-------|-------|
| ID | `food_variety_en` |
| KB ref | `food_variety` |
| Language | English |
| Review status | **pending** |
| Source | WHO starter KB v0.1 — food_variety entry |

**Triggers (English):**
- "What kinds of food should I eat?"
- "What does a varied pregnancy diet include?"
- "What food should I eat during pregnancy?"
- "What kinds of food can I eat when pregnant?"
- "What varieties of food should I eat during pregnancy?"
- "What is a healthy varied diet for a pregnant woman?"

**Answer (English):**
> Aim for a variety of foods, including vegetables, fruit, whole grains, beans and
> other protein foods. Ask your health worker for advice about any individual dietary
> needs.

Reviewer action needed:
- [ ] Confirm the food groups listed are appropriate for the local dietary context.
- [ ] Confirm the answer does not inadvertently exclude locally important foods or
  imply supplements/doses.
- [ ] Approve or revise.

---

### 4 · `food_safety_en`

| Field | Value |
|-------|-------|
| ID | `food_safety_en` |
| KB ref | `food_safety` |
| Language | English |
| Review status | **pending** |
| Source | WHO starter KB v0.1 — food_safety entry |

**Triggers (English):**
- "Does food cleanliness matter in pregnancy?"
- "Should I make sure food is safe and clean during pregnancy?"
- "Is food safety important when pregnant?"
- "Should food be safe and clean during pregnancy?"
- "Why is clean and safe food important in pregnancy?"
- "How do I keep food safe during pregnancy?"

**Answer (English):**
> Make sure the food you eat is safe and clean. Ask your health worker if you need
> more information about food safety during pregnancy.

Reviewer action needed:
- [ ] Verify this general guidance is accurate without specific cooking/storage
  instructions that could be misapplied.
- [ ] Approve or revise.

---

### 5 · `birth_preparation_en`

| Field | Value |
|-------|-------|
| ID | `birth_preparation_en` |
| KB ref | `birth_preparation` |
| Language | English |
| Review status | **pending** |
| Source | WHO starter KB v0.1 — birth_preparation entry |

**Triggers (English):**
- "What should I discuss when planning for birth?"
- "Should I plan where I will give birth?"
- "How should I prepare for childbirth?"
- "Should I plan and prepare for where I will give birth?"
- "What is a birth preparedness plan?"
- "How do I plan for birth and complications?"

**Answer (English):**
> Discuss where you will receive care for childbirth with your health worker. Make a
> birth-preparedness and complication-readiness plan with their guidance.

Reviewer action needed:
- [ ] Confirm the answer does not imply a recommendation for a specific facility type.
- [ ] Confirm the answer is consistent with the Kenya MoH birth-preparedness guidance.
- [ ] Approve or revise.

---

## Follow-up work (not completed in v0)

- **Kiswahili translations:** Prepare draft translations; submit for fluent-speaker and
  clinical review; add `language: sw` cards only after sign-off.
- **Sheng matching phrases:** Add to trigger lists after community review.
- **Full ~60-card library:** Extend to cover ANC contacts, discomforts, danger signs
  awareness, newborn care, breastfeeding — each requiring its own clinical source and
  review cycle.
- **Kenya MoH alignment:** Compare every entry against the appropriate Kenya Ministry
  of Health maternal-care material before describing this as Kenya-handbook-based content.
