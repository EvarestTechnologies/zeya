"""
Evaluation corpus for the danger-sign gate and the answer card matcher.

The data lives in ocs/tests/danger_eval_corpus.csv (issue #20). This module loads it.
Every row cites a section of docs/zeya-knowledge-base.md. Nothing comes from general
clinical knowledge.

Columns
    id, language, message, expected_label, expected_categories, expected_card,
    kb_section, note, batch

Labels
    EMERGENCY  The knowledge base says go to a facility now (handbook danger signs,
               the related symptoms in section 7, the mother after birth in
               section 11, the newborn in section 12, severe booklet readings).
    SAME_DAY   The knowledge base says go to the clinic, but not "now"
               (sections 1, 3, 6 and 11).
    ROUTINE    Everything else, including questions ABOUT danger signs, which the
               gate must not treat as an emergency.

expected_categories is a "|"-separated list of gate categories for EMERGENCY rows.
"pallor_anaemia" is the proposed ninth category. "newborn" is outside the gate's
current scope and is reported separately.

expected_card is the answer card a ROUTINE question should match (ids in
ocs/eval/cards.py), or empty where no card applies or the knowledge base is silent.

batch
    v1  the first 200 rows, 12 November 2026. The draft gate in
        ocs/eval/proposed_danger_gate.py was written while looking at these.
    v2  rows added 18 November 2026 for Sheng, spelling mistakes, danger-word traps
        and card questions. The draft gate was not tuned on them.

language is en, sw, sheng or mixed (Swahili and English switched within a message).

Every Swahili, Sheng and mixed message, and every label, is a draft that needs Achar's
review, and Sheng rows also need a native speaker.
"""

import csv
from pathlib import Path
from typing import NamedTuple

CORPUS_CSV = Path(__file__).resolve().parent.parent / "tests" / "danger_eval_corpus.csv"

LABELS = ("EMERGENCY", "SAME_DAY", "ROUTINE")
LANGUAGES = ("en", "sw", "sheng", "mixed")
CATEGORIES = (
    "bleeding",
    "headache_vision",
    "pallor_anaemia",
    "fever",
    "abdominal_pain",
    "swelling",
    "fetal_movement",
    "water_breaking",
    "convulsions",
    "newborn",
)
# Knowledge base section numbers, plus "registration" for greetings and sign-up replies.
KB_SECTIONS = tuple(str(n) for n in range(1, 14)) + ("registration",)


class Case(NamedTuple):
    id: str
    lang: str
    text: str
    label: str
    category: str | None  # the first expected category, or None
    kb: str
    note: str = ""
    categories: tuple = ()
    card: str = ""
    batch: str = "v1"


def _row_to_case(row: dict) -> Case:
    categories = tuple(c for c in row["expected_categories"].split("|") if c)
    return Case(
        id=row["id"],
        lang=row["language"],
        text=row["message"],
        label=row["expected_label"],
        category=categories[0] if categories else None,
        kb=row["kb_section"],
        note=row["note"],
        categories=categories,
        card=row["expected_card"],
        batch=row["batch"],
    )


def load(path: Path = CORPUS_CSV) -> list[Case]:
    with open(path, newline="", encoding="utf-8") as f:
        return [_row_to_case(row) for row in csv.DictReader(f)]


CASES: list[Case] = load()
