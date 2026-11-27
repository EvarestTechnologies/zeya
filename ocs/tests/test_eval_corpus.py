"""
Integrity checks for the danger-gate evaluation corpus.

The corpus lives in ocs/tests/danger_eval_corpus.csv (issue #20) and is loaded by
ocs/eval/corpus.py. It is the yardstick for every pattern change and for the answer
card matcher, so its shape is pinned here.
"""

import csv
import re
from collections import Counter

from ocs.eval.cards import CARDS
from ocs.eval.corpus import CASES, CATEGORIES, CORPUS_CSV, KB_SECTIONS, LABELS, LANGUAGES

V3_COLUMNS = [
    "id",
    "language",
    "message",
    "expected_label",
    "expected_categories",
    "expected_card",
    "kb_section",
    "note",
]
NINE_SIGNS = [
    "bleeding",
    "headache_vision",
    "pallor_anaemia",
    "fever",
    "abdominal_pain",
    "swelling",
    "fetal_movement",
    "water_breaking",
    "convulsions",
]
# Words that make a routine message a trap for a keyword gate.
DANGER_WORDS = re.compile(
    r"bleed|blood|damu|headache|kichwa|pale|pauka|fever|homa|pain|maumivu|uchungu|tumbo|"
    r"swell|vimba|kick|move|mateke|cheza|water|maji|convuls|degedege|fit|faint|danger|hatari",
    re.IGNORECASE,
)


def test_csv_has_the_v3_columns_then_batch():
    with open(CORPUS_CSV, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == V3_COLUMNS + ["batch"]


def test_corpus_has_at_least_200_cases_with_unique_ids():
    assert len(CASES) >= 200
    assert len({c.id for c in CASES}) == len(CASES)


def test_every_case_has_a_valid_label_language_and_kb_section():
    for c in CASES:
        assert c.label in LABELS, c.id
        assert c.lang in LANGUAGES, c.id
        assert c.kb in KB_SECTIONS, c.id
        assert c.text.strip() == c.text and c.text, c.id
        assert c.batch in {"v1", "v2"}, c.id


def test_emergency_cases_name_gate_categories_and_others_do_not():
    for c in CASES:
        if c.label == "EMERGENCY":
            assert c.categories and set(c.categories) <= set(CATEGORIES), c.id
            assert c.category == c.categories[0], c.id
        else:
            assert c.categories == () and c.category is None, c.id


def test_all_nine_handbook_signs_are_covered_in_english_and_swahili():
    seen = Counter((cat, c.lang) for c in CASES if c.label == "EMERGENCY" for cat in c.categories)
    for category in NINE_SIGNS:
        assert seen[(category, "en")] >= 3, category
        assert seen[(category, "sw")] >= 3, category


def test_sheng_is_covered():
    sheng = [c for c in CASES if c.lang == "sheng"]
    assert len(sheng) >= 20
    covered = {cat for c in sheng if c.label == "EMERGENCY" for cat in c.categories}
    assert len(covered & set(NINE_SIGNS)) >= 7, covered


def test_spelling_mistakes_are_covered_as_mothers_type():
    typos = [c for c in CASES if "typo" in c.note]
    assert len(typos) >= 20
    assert sum(1 for c in typos if c.label == "EMERGENCY") >= 15


def test_at_least_40_routine_messages_use_a_danger_word():
    traps = [c for c in CASES if c.label == "ROUTINE" and DANGER_WORDS.search(c.text)]
    assert len(traps) >= 40, len(traps)


def test_at_least_80_routine_questions_name_the_card_they_should_match():
    with_card = [c for c in CASES if c.label == "ROUTINE" and c.card]
    assert len(with_card) >= 80, len(with_card)


def test_cards_exist_and_cite_the_same_kb_section_as_the_case():
    for c in CASES:
        if c.card:
            assert c.label == "ROUTINE", c.id
            assert c.card in CARDS, (c.id, c.card)
            assert CARDS[c.card].kb == c.kb, (c.id, c.card)


def test_corpus_includes_danger_sign_questions_that_must_not_trigger():
    questions = [c for c in CASES if c.label == "ROUTINE" and c.kb == "7"]
    assert len(questions) >= 10


def test_the_release_script_emergency_phrase_is_in_the_corpus():
    case = [c for c in CASES if c.text.lower() == "nina homa na kichwa kinauma sana"]
    assert case and case[0].label == "EMERGENCY"
    assert set(case[0].categories) == {"fever", "headache_vision"}
