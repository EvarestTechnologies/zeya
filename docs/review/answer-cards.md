# Answer cards review, release 1

**Reviewer:** Stella Oiro, licensed clinical officer
**Source:** `docs/answer-cards.yaml`, built from `docs/zeya-knowledge-base.md`
**Sign-off:** `docs/review/clinical-signoff.md`, item B2

The five Ministry of Health cards replace the starter cards slot for slot (work order task 3). Each answer is the knowledge entry text exactly, in Mother and Child Health Handbook wording, and ends with its source label. The archived starter cards are in `docs/archive/who-starter/` with `review_status: pending`, and they are not loaded.

| Old slot | New card | Source |
|---|---|---|
| anc_purpose | anc_visits | HB p13, HB cover |
| pregnancy_records | danger_signs | HB p14 |
| food_variety | food_groups | HB p18 |
| food_safety | daily_care | HB p13 |
| birth_preparation | birth_plan | HB inside cover, HB p3 |

**Matching notes**
- **Trigger checks:** every trigger routes to its own card. Checked with the shipped matcher in the pinned sandbox.
- **Removed anchor words:** "eat" (food groups) and "plan" (birth plan) are not anchor words. As anchors they made "Something to eat please" and "How should I plan?" match a card. So "What should I eat during pregnancy?" reaches the AI, which answers from the food groups entry. "What foods should I eat during pregnancy?" reaches the card.
- **Old false-positive tests:** the matcher tests that described the old food safety topic now use daily care questions about water, rest and nets.

## English cards

### `anc_visits_en`

- **Status:** approved (sign-off B2, 27 November 2026)
- **Knowledge entry:** `anc_visits`, source HB p13, HB cover
- **Words:** 41 (limit 79)
- **Topic anchors:** anc, antenatal, clinic, visit, visits, prenatal, handbook

Answer:

> Go for your first antenatal visit as soon as possible, and attend 8 times during your pregnancy. Carry your Mother and Child Health Handbook to every visit and show it to the health worker.
> Source: MOH Mother and Child Health Handbook.

Triggers:

- Why should I go to ANC?
- When should I start antenatal clinic?
- How many antenatal visits do I need?
- How many times should I go to clinic when pregnant?
- When is my first antenatal visit?
- Why should I attend antenatal clinic?
- What should I carry to the antenatal clinic?

### `danger_signs_en`

- **Status:** approved (sign-off B2, 27 November 2026)
- **Knowledge entry:** `danger_signs`, source HB p14
- **Words:** 53 (limit 79)
- **Topic anchors:** danger, signs, warning, hospital

Answer:

> Danger signs in pregnancy: severe headache, looking pale, vaginal bleeding, fever, severe abdominal pain, swelling of the face and hands, reduced or no movement of the baby, breaking water, and convulsions or fits. If you have any of these signs, go to a health facility now.
> Source: MOH Mother and Child Health Handbook.

Triggers:

- What are the danger signs in pregnancy?
- Which signs mean I should go to hospital?
- What danger signs should I watch for?
- What are the warning signs during pregnancy?
- When should I go to hospital when pregnant?

### `daily_care_en`

- **Status:** approved (sign-off B2, 27 November 2026)
- **Knowledge entry:** `daily_care`, source HB p13
- **Words:** 49 (limit 79)
- **Topic anchors:** care, water, rest, net, exercise, iron, daily, meal

Answer:

> Eat one extra meal every day. Drink plenty of water, at least 8 glasses a day. Take iron and folic acid supplements every day throughout pregnancy. Avoid heavy work and rest more. Sleep under a long-lasting insecticidal net. Do regular gentle exercise.
> Source: MOH Mother and Child Health Handbook.

Triggers:

- How should I take care of myself during pregnancy?
- What daily care do I need when pregnant?
- How much water should I drink in pregnancy?
- Should I rest more when pregnant?
- Should I sleep under a mosquito net when pregnant?
- Should I take iron and folic acid every day?

### `food_groups_en`

- **Status:** approved (sign-off B2, 27 November 2026)
- **Knowledge entry:** `food_groups`, source HB p18
- **Words:** 57 (limit 79)
- **Topic anchors:** food, foods, diet, nutrition, groups

Answer:

> Eat at least 5 of the 10 food groups every day: grains and starchy foods, legumes and pulses, nuts and seeds, dairy, eggs, meat, fish and poultry, orange and yellow fruits and vegetables, dark green leafy vegetables, other vegetables, and other fruits. Eat a variety of foods within each group.
> Source: MOH Mother and Child Health Handbook.

Triggers:

- What foods should I eat during pregnancy?
- Which foods are good in pregnancy?
- What are the food groups?
- What food should I eat when pregnant?
- How many food groups should I eat?
- What is a good diet in pregnancy?

### `birth_plan_en`

- **Status:** approved (sign-off B2, 27 November 2026)
- **Knowledge entry:** `birth_plan`, source HB inside cover, HB p3
- **Words:** 58 (limit 79)
- **Topic anchors:** birth, delivery, deliver, prepare, childbirth, husband, partner

Answer:

> Make a birth plan with your health worker: expected date of birth, the health facility where you will give birth, who will attend you, the facility's phone number, your birth companion, transport and a blood donor. Your partner can help by arranging transport, money, a birth companion and an emergency kit.
> Source: MOH Mother and Child Health Handbook.

Triggers:

- What should be in my birth plan?
- How do I prepare for birth?
- How do I make a birth plan?
- How can my husband help me prepare for birth?
- What do I need to prepare before delivery?
- How do I plan for delivery?
