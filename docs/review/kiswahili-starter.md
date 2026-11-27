# Kiswahili starter cards — review record

**Status: Starter runtime content eligible. This record is not publication evidence.**

This document lists the five Kiswahili (sw) answer cards and KB entries in
`docs/answer-cards.yaml` and `docs/zeya-knowledge-base.md`.
They have approved runtime eligibility. Hosted publication remains separate
from this content record.

---

## Translation status and limitations

These five Kiswahili translations were machine-authored by an AI model for
the purpose of establishing the data schema and test coverage. No clinical
validation is claimed. The entries and cards have `approved` runtime eligibility;
production still excludes any records whose eligibility is `pending`.

**Specific limitations (must be verified by a fluent reviewer):**

- Swahili register may be inappropriate for the target audience (pregnant women in
  Kenya, including trial participants in Migori County). The translations use a formal/standard register; a reviewer
  should confirm whether a more colloquial register is appropriate.
- Medical terminology (e.g. "kabla ya kujifungua", "mfanyakazi wa afya") must be
  confirmed as correct and locally used terms in the Kenyan maternal health context.
- "Mfanyakazi wa afya" is used for "health worker" — confirm this is the preferred
  term over alternatives (e.g. "daktari", "muuguzi", "mama wa afya").
- The trigger strings are natural Swahili paraphrases of the English trigger vocabulary,
  designed for the word-overlap matcher. A fluent-speaker reviewer should confirm they
  represent questions that pregnant women in Kenya would actually ask in Swahili.
- Topic anchors include Swahili words used by the matcher for eligibility checks.
  These are technical parameters and do not require clinical review, but must be
  verified correct by a Swahili-language reviewer.
- No Sheng, regional dialect, or SMS-abbreviated forms have been included. These
  require separate community review.

**What was NOT changed from the English versions:**

- Source references (WHO links retained verbatim)
- Scope (general antenatal education only)
- Absence of diagnoses, drug doses, emergency contacts, or facility-specific guidance
- pending review_status (identical to English cards)

---

## Scope and limitations (same as English cards)

These five sw draft cards cover general antenatal education only, translated from
the five-entry WHO-linked starter KB (`zeya-knowledge-base.md`, v0.1 en entries).
They do not provide diagnoses, prescriptions, drug doses, symptom assessments,
emergency guidance or facility-specific information.

The unsupported-question fallback message remains:
- **English:** "I do not have reviewed information to answer that question. Please
  ask your healthcare provider."
- **Swahili (DRAFT — pending fluent-speaker and clinical review):** "Sina taarifa
  iliyokaguliwa kujibu swali hilo. Tafadhali uliza mtoa huduma wako wa afya."

---

## Draft sw KB entries and cards pending review

### 1 · `anc_purpose` (sw)

| Field | Value |
|-------|-------|
| KB ID | `anc_purpose` |
| Card ID | `anc_purpose_sw` |
| Language | Kiswahili (sw) |
| Review status | **pending** |
| KB source | WHO starter KB v0.1 — anc_purpose entry (en) |
| Card source | Translator-drafted from KB body above |

**KB body (Swahili draft):**
> Ziara za kabla ya kujifungua hutoa huduma ya afya, taarifa, ushauri na msaada
> wa kihisia wakati wa ujauzito. Wasiliana na mfanyakazi wa afya baada ya
> kuthibitisha ujauzito wako, na uhudhurie ziara wanazopendekeza.

**Triggers (Swahili — natural paraphrases for the word-overlap matcher):**
- "Niende kliniki ya ujauzito kwa nini?"
- "Ziara za ujauzito ni kwa nini?"
- "Niende ANC kwa sababu gani?"
- "Huduma ya kabla ya kujifungua ni kwa nini?"
- "Nini lengo la ziara za ANC?"
- "Kwa nini ninahitaji kuhudhuria ziara za kabla ya kujifungua?"

**Topic anchors:** `anc`, `ujauzito`, `kliniki`, `ziara`

Reviewer action needed:
- [ ] Verify Swahili phrasing is natural and appropriate for the Kenyan context.
- [ ] Confirm "kabla ya kujifungua" is the standard term for antenatal period.
- [ ] Confirm "mfanyakazi wa afya" is the preferred term for health worker.
- [ ] Confirm triggers represent questions pregnant women would actually ask.
- [ ] Approve or revise; set `review_status: approved` only after explicit sign-off.

---

### 2 · `pregnancy_records` (sw)

| Field | Value |
|-------|-------|
| KB ID | `pregnancy_records` |
| Card ID | `pregnancy_records_sw` |
| Language | Kiswahili (sw) |
| Review status | **pending** |
| KB source | WHO starter KB v0.1 — pregnancy_records entry (en) |

**KB body (Swahili draft):**
> Hifadhi rekodi ya huduma yako ya afya ya ujauzito na chanjo nyumbani. Muulize
> mfanyakazi wako wa afya akueleze taarifa katika rekodi zako ambazo huelewi.

**Triggers:**
- "Je, nihifadhi rekodi zangu za ujauzito?"
- "Kwa nini nishike kumbukumbu za huduma ya ujauzito?"
- "Vipi niandike rekodi za afya ya ujauzito wangu?"
- "Ni muhimu kushika rekodi za ujauzito?"
- "Kwa nini kuweka rekodi ya afya ya ujauzito ni muhimu?"
- "Ninahifadhije rekodi zangu za afya ya uzazi?"

**Topic anchors:** `rekodi`, `kumbukumbu`, `hifadhi`

Reviewer action needed:
- [ ] Confirm "rekodi" is the preferred term over "kumbukumbu" for health records
  in this context (both are used in the triggers for coverage).
- [ ] Confirm "chanjo" (vaccines) is the correct Swahili term.
- [ ] Confirm triggers represent questions about pregnancy record-keeping.
- [ ] Approve or revise.

---

### 3 · `food_variety` (sw)

| Field | Value |
|-------|-------|
| KB ID | `food_variety` |
| Card ID | `food_variety_sw` |
| Language | Kiswahili (sw) |
| Review status | **pending** |
| KB source | WHO starter KB v0.1 — food_variety entry (en) |

**KB body (Swahili draft):**
> Jaribu kuwa na aina mbalimbali za vyakula, ikiwemo mboga, matunda, nafaka zisizokobolewa,
> maharagwe na vyakula vingine vya protini. Muulize mfanyakazi wako wa afya
> ushauri kuhusu mahitaji yoyote ya lishe ya kibinafsi.

**Triggers:**
- "Ninapaswa kula chakula gani wakati wa ujauzito?"
- "Nini lishe nzuri kwa mjamzito?"
- "Nini chakula cha aina mbalimbali kwa mjamzito?"
- "Ninaweza kula nini wakati wa ujauzito?"
- "Nini inajumuishwa katika lishe ya aina mbalimbali ya ujauzito?"
- "Ni lishe gani nzuri ya mjamzito?"

**Topic anchors:** `chakula`, `kula`, `lishe`, `mboga`, `matunda`

Reviewer action needed:
- [ ] Confirm "mjamzito" is the preferred term for a pregnant woman in this context.
- [ ] Confirm "nafaka zisizokobolewa" faithfully conveys "whole grains" for the audience.
- [ ] Confirm listed food groups (mboga, matunda, nafaka zisizokobolewa, maharagwe) are appropriate
  for the local dietary context and do not exclude locally important foods.
- [ ] Confirm the answer does not inadvertently imply supplements or specific doses.
- [ ] Confirm triggers represent questions about pregnancy nutrition in Swahili.
- [ ] Approve or revise.

---

### 4 · `food_safety` (sw)

| Field | Value |
|-------|-------|
| KB ID | `food_safety` |
| Card ID | `food_safety_sw` |
| Language | Kiswahili (sw) |
| Review status | **pending** |
| KB source | WHO starter KB v0.1 — food_safety entry (en) |

**KB body (Swahili draft):**
> Hakikisha chakula unachokula ni salama na safi. Muulize mfanyakazi wako wa
> afya ikiwa unahitaji taarifa zaidi kuhusu usalama wa chakula wakati wa ujauzito.

**Triggers:**
- "Je, usafi wa chakula ni muhimu wakati wa ujauzito?"
- "Ninahakikishaje chakula ni salama na safi wakati wa ujauzito?"
- "Usalama wa chakula ni muhimu kwa mjamzito?"
- "Chakula kiwe salama na safi wakati wa ujauzito?"
- "Kwa nini chakula salama na safi ni muhimu katika ujauzito?"
- "Ninahifadhije usalama wa chakula wakati wa ujauzito?"

**Topic anchors:** `chakula`, `kula`, `lishe`

Reviewer action needed:
- [ ] Verify general food safety guidance is accurate without specific cooking or
  storage instructions that could be misapplied.
- [ ] Confirm "salama na safi" adequately covers food safety and cleanliness
  in the Kenyan maternal context.
- [ ] Confirm triggers represent food safety questions from pregnant women.
- [ ] Approve or revise.

---

### 5 · `birth_preparation` (sw)

| Field | Value |
|-------|-------|
| KB ID | `birth_preparation` |
| Card ID | `birth_preparation_sw` |
| Language | Kiswahili (sw) |
| Review status | **pending** |
| KB source | WHO starter KB v0.1 — birth_preparation entry (en) |

**KB body (Swahili draft):**
> Jadili na mfanyakazi wako wa afya mahali ambapo utapata huduma ya kujifungua.
> Fanya mpango wa kujiandaa kwa kujifungua na mpango wa kukabiliana na matatizo
> kwa mwongozo wao.

**Triggers:**
- "Ninapaswa kujadili nini kuhusu mipango ya kujifungua?"
- "Je, nipange mahali pa kujifungua?"
- "Nijiandaeje kwa kujifungua?"
- "Nini mpango wa kujiandaa kwa kujifungua?"
- "Nijiandaeje kwa kujifungua na matatizo yanayoweza kutokea?"
- "Nini maandalizi ya kujifungua?"

**Topic anchors:** `kujifungua`, `mpango`, `maandalizi`, `uzazi`

Reviewer action needed:
- [ ] Confirm "kujifungua" is the standard Swahili term for childbirth in this context.
- [ ] Confirm "kukabiliana na matatizo" adequately conveys complication readiness
  without implying specific medical interventions.
- [ ] Confirm the answer does not imply a recommendation for a specific facility type.
- [ ] Confirm triggers represent birth planning questions from pregnant women.
- [ ] Approve or revise.

---

## Local technical checks and matching limitations

The permanent tests execute the rendered KB-selection, card-matching and output-guard
nodes in the pinned local RestrictedPython sandbox. Five authored non-trigger
questions assert the exact expected Kiswahili card ID and delivered answer. These
are authored regression examples, not held-out language evaluation, hosted OCS
execution, handset delivery or clinical validation. Separate checks verify that
the actual default builder excludes pending content for both saved languages.

Generic food wording remains ambiguous under the inherited word-overlap matcher.
Local probe observations with the pending cards enabled only in the sandbox were:

- `chakula lishe` -> `ASK_AI` (no card).
- `Je chakula ni muhimu wakati wa ujauzito?` -> `food_safety_sw`.
- `chakula salama aina mbalimbali` -> `food_variety_sw`.

These observations are not claims that the selected topic is appropriate for
every interpretation. Reviewers should assess generic nutrition/food-safety
questions and near-ties before participant use. This draft does not modify the
production matcher or claim broad Kiswahili matching accuracy.

## Follow-up work (not completed in feat/kiswahili-starter-cards)

- **Fluent-speaker review:** Every sw entry and card trigger/answer must be reviewed
  by a fluent Kiswahili speaker with community health context before approval.
- **Clinical review:** Every sw card answer must be reviewed by a clinician
  (preferably Achar or Kenya MoH-aligned reviewer) for clinical accuracy.
- **Register and dialect:** Community review for appropriate register, Sheng inclusion
  and regional dialect variations.
- **Swahili matcher improvements:** The current Jaccard matcher uses English stemming
  and stopwords; natural Swahili question coverage depends on shared vocabulary
  with trigger strings. A Swahili-aware tokenizer/stopword list is a possible
  follow-up, but any improvement requires evaluation rather than assuming that
  a tokenizer change improves accuracy.
- **Kenya MoH alignment:** Compare every sw entry against Kenya MoH maternal-care
  material in Swahili before describing this as Kenya-handbook-based content.
- **Full ~60-card library:** Extend to cover ANC contacts, discomforts, danger signs
  awareness, newborn care, breastfeeding — each requiring its own clinical source
  and both English and Swahili review cycles.
