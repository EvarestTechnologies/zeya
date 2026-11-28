"""
Provisional answer card catalogue (issue #20, used by issue #23).

These are card IDs only, with the knowledge base section and source pages each card
must be drafted from. The card text does not exist yet: issue #23 writes it in
docs/answer-cards.yaml, which must use these IDs, and Achar approves every card.

pending=True means the card relies on a knowledge base block marked "pending", so it
cannot go live until Achar approves that block.
"""

from typing import NamedTuple


class Card(NamedTuple):
    kb: str
    source: str
    pending: bool = False


CARDS: dict[str, Card] = {
    # 1. The eight ANC contacts
    "anc_schedule": Card("1", "NG24 p104, p105"),
    "anc_first_visit": Card("1", "NG24 p104"),
    # 2. What is checked at clinic
    "clinic_checks": Card("2", "HB p8"),
    "first_visit_tests": Card("2", "NG24 p112, HB p5 to p7"),
    "ultrasound": Card("2", "HB p7, NG24 p101"),
    # 3. Reading the booklet
    "bp_reading": Card("3", "BOP p15"),
    "hb_reading": Card("3", "BOP p38, p40"),
    "baby_heart_rate": Card("3", "BOP p26"),
    "urine_test": Card("3", "BOP p58"),
    "birth_weight": Card("3", "NG24 p659"),
    "weight_gain": Card("3", "HB p8, NG24 p34", pending=True),
    # 4. Preventive care
    "iron_folic": Card("4", "HB p10, NG24 p100"),
    "calcium": Card("4", "NG24 p104, BOP p16"),
    "malaria_prevention": Card("4", "NG24 p110, HB p10"),
    "bed_net": Card("4", "HB p10, p13"),
    "deworming": Card("4", "HB p10, NG24 p110"),
    "tetanus_vaccine": Card("4", "HB p10, NG24 p110"),
    "vitamin_a": Card("4", "NG24 p42, p109"),
    "rhesus": Card("4", "NG24 p104"),
    # 5. Daily care and food
    "food_general": Card("5", "HB p13, p18"),
    "food_groups": Card("5", "HB p18"),
    "water_intake": Card("5", "HB p13"),
    "rest_heavy_work": Card("5", "HB p13"),
    "exercise": Card("5", "HB p13"),
    "dental": Card("5", "HB p13"),
    "iron_rich_foods": Card("5", "NG12 p38 to p44", pending=True),
    "tea_with_meals": Card("5", "NG12 p38 to p44", pending=True),
    "calcium_foods": Card("5", "NG12 p38 to p44", pending=True),
    # 6. Common discomforts
    "nausea": Card("6", "NG24 p52 to p55"),
    "heartburn": Card("6", "NG12 p50", pending=True),
    "constipation": Card("6", "NG12 p50, p51", pending=True),
    "soil_craving": Card("6", "NG12 p51, BOP p39", pending=True),
    "poor_appetite": Card("6", "NG12 p51", pending=True),
    # 7. Danger signs in pregnancy
    "danger_signs": Card("7", "HB p14, BOP p15, p26, p39, p46"),
    "baby_movement": Card("7", "HB p14, NG12 p173", pending=True),
    # 8. Higher risk mothers
    "high_risk": Card("8", "BOP p12, NG24 p112 to p116"),
    # 9. Birth plan and the father
    "birth_plan": Card("9", "HB inside cover"),
    "father_role": Card("9", "HB p3, p4"),
    # 10. Labour and birth
    "labour_signs": Card("10", "NG12 p172", pending=True),
    "labour_length": Card("10", "NG24 p303, p307"),
    "birth_companion": Card("10", "NG24 p299"),
    "labour_eating": Card("10", "NG24 p302"),
    "birth_position": Card("10", "NG24 p302, p303"),
    "labour_pain_relief": Card("10", "NG24 p302"),
    "hospital_stay": Card("10", "NG24 p307"),
    "labour_danger_signs": Card("10", "NG12 p65", pending=True),
    # 11. The mother after birth
    "postnatal_danger_signs": Card("11", "HB p19, BOP p15, p20, p31"),
    "postnatal_checks": Card("11", "HB p20"),
    "breastfeeding_food": Card("11", "HB p18, NG24 p51"),
    "family_planning": Card("11", "HB p4"),
    "baby_blues": Card("11", "NG24 p286 to p291"),
    # 12. The newborn
    "newborn_first_hour": Card("12", "NG24 p645 to p654, HB p15"),
    "newborn_vaccines": Card("12", "NG24 p660"),
    "newborn_bath": Card("12", "NG24 p645 to p654"),
    "exclusive_breastfeeding": Card("12", "NG24 p660 to p662, HB p18"),
    "cord_care": Card("12", "NG24 p660 to p662, HB p18"),
    "newborn_warmth": Card("12", "NG24 p660 to p662, HB p18"),
    "newborn_sleep": Card("12", "NG24 p660 to p662, HB p18"),
    "kangaroo_care": Card("12", "HB p15"),
    "home_birth": Card("12", "HB p18"),
    "newborn_danger_signs": Card("12", "HB p19, NG24 p661"),
    "breastfeeding_position": Card("12", "HB p16"),
    # 13. HIV, syphilis and hepatitis B
    "hiv_testing": Card("13", "HB p7, p11"),
    "hiv_baby": Card("13", "HB p3, p12, p36, p44"),
    "hiv_breastfeeding": Card("13", "NG24 p654"),
}
