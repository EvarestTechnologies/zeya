"""Kiswahili (sw) starter KB entries and answer cards — TDD test file.

Scope
-----
Verifies that:
  1. Each of the five English KB topics has a corresponding pending sw KB entry
     with the same topic ID and language "sw".
  2. Each of the five English answer cards has a corresponding pending sw card
     with a "_sw"-suffixed ID and the correct kb_ref.
  3. SW cards are absent from the default (approved-only) production build.
  4. The finite authored in-scope Swahili questions return their exact expected
     Swahili cards; this is regression coverage, not held-out accuracy evidence.
  5. English trigger text does NOT match for a "sw"-language participant
     (language eligibility guard).
  6. Wrong-topic/unrelated/uncertain fallback for Swahili questions also
     routes ASK_AI (no forced wrong-card).

TDD Evidence Log
----------------
The original combined pre-data run recorded 10 behavioral failures and 26
passes in RED-slice1-and-2.log. It was not two separately recorded vertical
RED/GREEN slices. Production-exclusion checks pin existing invariants;
the parent subsequently strengthened matching assertions and added real
KB -> matcher -> guard consumer checks in test_kiswahili_card_chain.py.

Content status: translator-drafted, NOT fluent/clinical approved, all pending.
No matcher or knowledge-production Python changed.
Tests use existing NodeHarness + RestrictedPython harness via include_pending=True
for local staging only — never allow_pending in production.
"""

import pathlib

import pytest

CARDS_PATH = pathlib.Path(__file__).resolve().parents[2] / "docs" / "answer-cards.yaml"
KB_PATH = pathlib.Path(__file__).resolve().parents[2] / "docs" / "zeya-knowledge-base.md"

_import_exc: Exception | None = None
try:
    from ocs.answer_cards import load_answer_cards, render_answer_match
    from ocs.knowledge import load_knowledge
    from ocs.tests.sandbox import NodeHarness

    _IMPORT_OK = True
except Exception as _exc:  # noqa: BLE001
    _IMPORT_OK = False
    _import_exc = _exc


def _require_import():
    if not _IMPORT_OK:
        pytest.fail(f"Cannot import ocs modules: {_import_exc!r}")


# Five topic IDs that must each have both en and sw KB entries.
FIVE_TOPIC_IDS = {
    "anc_visits",
    "danger_signs",
    "food_groups",
    "daily_care",
    "birth_plan",
}

ALL_KB_IDS = list(FIVE_TOPIC_IDS)

# Card ID expectations: English IDs exist; sw IDs follow the _sw suffix convention.
EN_CARD_IDS = {
    "anc_visits_en",
    "danger_signs_en",
    "food_groups_en",
    "daily_care_en",
    "birth_plan_en",
}
SW_CARD_IDS = {
    "anc_visits_sw",
    "danger_signs_sw",
    "food_groups_sw",
    "daily_care_sw",
    "birth_plan_sw",
}


# ---------------------------------------------------------------------------
# Slice 1 RED → GREEN: KB counterpart coverage
#
# RED before sw entries added to docs/zeya-knowledge-base.md.
# GREEN after addition.  This is the first failing test per TDD contract.
# ---------------------------------------------------------------------------


class TestKBCounterpartCoverage:
    """Every English KB topic must have a corresponding pending sw entry.

    SLICE 1: This class must fail (RED) before sw entries are added to the
    knowledge base, and pass (GREEN) after they are added.
    """

    def test_sw_kb_entries_exist_for_all_five_topics(self):
        """Each en KB topic ID must have a corresponding sw KB entry.

        RED state: no sw entries in docs/zeya-knowledge-base.md.
        GREEN state: five sw entries added.
        """
        _require_import()
        entries = load_knowledge(KB_PATH, include_pending=True)
        sw_ids = {e["id"] for e in entries if e["language"] == "sw"}
        missing = FIVE_TOPIC_IDS - sw_ids
        assert missing == set(), (
            f"Missing sw KB entries for topics: {missing}. "
            "Each English topic must have a corresponding pending sw entry."
        )

    def test_all_sw_kb_entries_are_approved(self):
        """All sw KB entries must be approved for production eligibility."""
        _require_import()
        entries = load_knowledge(KB_PATH, include_pending=True)
        sw_entries = [e for e in entries if e["language"] == "sw"]
        assert len(sw_entries) == 5, f"Expected 5 sw KB entries, got {len(sw_entries)}"
        for entry in sw_entries:
            assert entry["review_status"] == "approved", (
                f"sw KB entry '{entry['id']}' must be approved — "
                "owner has approved the Kiswahili starter pack for production eligibility."
            )

    def test_sw_kb_entries_have_matching_topic_ids(self):
        """sw KB entry IDs must exactly match the five English topic IDs."""
        _require_import()
        entries = load_knowledge(KB_PATH, include_pending=True)
        sw_ids = {e["id"] for e in entries if e["language"] == "sw"}
        assert sw_ids == FIVE_TOPIC_IDS, (
            f"sw KB entry IDs {sw_ids!r} must exactly match {FIVE_TOPIC_IDS!r}. "
            "Each sw entry uses the same topic ID, differentiated only by language field."
        )

    def test_sw_kb_entries_have_source_refs(self):
        """sw KB entries must retain the same WHO source refs as their en counterparts."""
        _require_import()
        entries = load_knowledge(KB_PATH, include_pending=True)
        sw_entries = {e["id"]: e for e in entries if e["language"] == "sw"}
        en_entries = {e["id"]: e for e in entries if e["language"] == "en"}
        for topic_id in FIVE_TOPIC_IDS:
            entry = sw_entries.get(topic_id)
            assert entry is not None, f"Missing sw entry for topic '{topic_id}'"
            assert entry["source_refs"] == en_entries[topic_id]["source_refs"], (
                f"sw KB entry '{topic_id}' must retain its English counterpart's exact source references."
            )

    def test_sw_kb_entries_have_nonempty_body(self):
        """Every sw KB entry must have non-empty body text (the Swahili draft translation)."""
        _require_import()
        entries = load_knowledge(KB_PATH, include_pending=True)
        sw_entries = [e for e in entries if e["language"] == "sw"]
        for entry in sw_entries:
            assert entry["text"].strip(), f"sw KB entry '{entry['id']}' has empty body text."

    def test_sw_kb_entries_included_in_default_production_load(self):
        """Default load (include_pending=False) must return 5 sw entries — all approved."""
        _require_import()
        entries = load_knowledge(KB_PATH)  # default: include_pending=False
        sw_entries = [e for e in entries if e["language"] == "sw"]
        assert len(sw_entries) == 5, (
            f"Expected 5 sw KB entries in production load; found: {[e['id'] for e in sw_entries]}"
        )


# ---------------------------------------------------------------------------
# Slice 2 RED → GREEN: Answer-card counterpart coverage
#
# RED before sw cards added to docs/answer-cards.yaml.
# GREEN after addition.
# ---------------------------------------------------------------------------


class TestCardCounterpartCoverage:
    """Every English answer card must have a corresponding pending sw card.

    SLICE 2: This class must fail (RED) before sw cards are added to the
    answer-cards YAML, and pass (GREEN) after they are added.
    """

    def test_sw_cards_exist_for_all_five_topics(self):
        """Each of the five topics must have a sw card with the _sw ID suffix.

        RED state: no sw cards in docs/answer-cards.yaml.
        GREEN state: five sw cards added.
        """
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        sw_ids = {c["id"] for c in cards if c.get("language") == "sw"}
        missing = SW_CARD_IDS - sw_ids
        assert missing == set(), (
            f"Missing sw answer cards: {missing}. Each topic must have a pending sw card with _sw ID suffix."
        )

    def test_all_sw_cards_are_approved(self):
        """All five sw answer cards must be approved for production eligibility."""
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        sw_cards = [c for c in cards if c.get("language") == "sw"]
        assert len(sw_cards) == 5, f"Expected 5 sw cards, got {len(sw_cards)}"
        for card in sw_cards:
            assert card["review_status"] == "approved", (
                f"sw card '{card['id']}' must be approved — owner has approved the Kiswahili starter pack."
            )

    def test_sw_card_ids_are_exactly_the_five_expected(self):
        """sw card IDs must exactly match the expected set (no extras, no missing)."""
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        sw_ids = {c["id"] for c in cards if c.get("language") == "sw"}
        assert sw_ids == SW_CARD_IDS, f"sw card IDs {sw_ids!r} must exactly equal {SW_CARD_IDS!r}."

    def test_sw_cards_have_correct_kb_refs(self):
        """Each sw card must reference its corresponding KB topic ID."""
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        sw_cards = {c["id"]: c for c in cards if c.get("language") == "sw"}
        for sw_id in SW_CARD_IDS:
            card = sw_cards.get(sw_id)
            assert card is not None, f"Missing sw card '{sw_id}'"
            # _sw suffix → kb_ref should be the topic without suffix
            expected_kb_ref = sw_id.replace("_sw", "")
            assert card["kb_ref"] == expected_kb_ref, (
                f"sw card '{sw_id}' has kb_ref={card['kb_ref']!r}; expected {expected_kb_ref!r}."
            )

    def test_sw_cards_have_swahili_triggers(self):
        """sw cards must have at least one trigger string each."""
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        sw_cards = [c for c in cards if c.get("language") == "sw"]
        for card in sw_cards:
            assert isinstance(card["triggers"], list) and len(card["triggers"]) >= 1, (
                f"sw card '{card['id']}' has no triggers."
            )
            for t in card["triggers"]:
                assert isinstance(t, str) and t.strip(), f"sw card '{card['id']}' has empty trigger: {t!r}"

    def test_sw_cards_have_topic_anchors(self):
        """sw cards must have non-empty topic_anchors for eligibility matching."""
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        sw_cards = [c for c in cards if c.get("language") == "sw"]
        for card in sw_cards:
            assert isinstance(card.get("topic_anchors"), list) and len(card["topic_anchors"]) >= 1, (
                f"sw card '{card['id']}' has no topic_anchors."
            )

    def test_sw_cards_have_nonempty_answers(self):
        """Every sw card must have non-empty answer text (the Swahili draft translation)."""
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        sw_cards = [c for c in cards if c.get("language") == "sw"]
        for card in sw_cards:
            assert card.get("answer", "").strip(), f"sw card '{card['id']}' has empty answer text."

    def test_sw_cards_included_in_default_production_build(self):
        """Default load (include_pending=False) must return 5 sw cards — all approved."""
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=False)
        sw_cards = [c for c in cards if c.get("language") == "sw"]
        assert len(sw_cards) == 5, f"Expected 5 sw cards in production build; found: {[c['id'] for c in sw_cards]}"


# ---------------------------------------------------------------------------
# Slice 3: Combined count invariants (after both KB and card data added)
#
# These are characterization tests for the combined 10-entry/10-card corpus.
# ---------------------------------------------------------------------------


class TestCombinedCorpusInvariants:
    """Combined invariants: 5 en + 5 sw entries/cards, all pending.

    Characterization tests: pin the full corpus shape after both slices GREEN.
    """

    def test_total_kb_entry_count_is_ten(self):
        """KB must contain exactly 10 entries: 5 en + 5 sw, all pending."""
        _require_import()
        entries = load_knowledge(KB_PATH, include_pending=True)
        assert len(entries) == 10, f"Expected 10 KB entries (5 en + 5 sw), got {len(entries)}"

    def test_total_card_count_is_ten(self):
        """Cards YAML must contain exactly 10 cards: 5 en + 5 sw, all pending."""
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        assert len(cards) == 10, f"Expected 10 answer cards (5 en + 5 sw), got {len(cards)}"

    def test_en_kb_entries_approved(self):
        """The five English KB entries must remain unchanged (IDs, language) and be approved."""
        _require_import()
        entries = load_knowledge(KB_PATH, include_pending=True)
        en_entries = [e for e in entries if e["language"] == "en"]
        en_ids = {e["id"] for e in en_entries}
        assert len(en_entries) == 5, f"Expected 5 en KB entries, got {len(en_entries)}"
        assert en_ids == FIVE_TOPIC_IDS, f"en IDs mismatch: {en_ids}"
        for entry in en_entries:
            assert entry["review_status"] == "approved"
            assert entry["language"] == "en"

    def test_en_cards_approved(self):
        """The five English answer cards must remain unchanged (IDs, language) and be approved."""
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        en_cards = [c for c in cards if c.get("language") == "en"]
        en_ids = {c["id"] for c in en_cards}
        assert len(en_cards) == 5, f"Expected 5 en cards, got {len(en_cards)}"
        assert en_ids == EN_CARD_IDS, f"en card IDs mismatch: {en_ids}"
        for card in en_cards:
            assert card["review_status"] == "approved"
            assert card["language"] == "en"

    def test_all_entries_either_en_or_sw(self):
        """Every KB entry must have language 'en' or 'sw' — no other language introduced."""
        _require_import()
        entries = load_knowledge(KB_PATH, include_pending=True)
        for entry in entries:
            assert entry["language"] in ("en", "sw"), (
                f"KB entry '{entry['id']}' has unexpected language {entry['language']!r}"
            )

    def test_all_cards_either_en_or_sw(self):
        """Every answer card must have language 'en' or 'sw'."""
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        for card in cards:
            assert card.get("language") in ("en", "sw"), (
                f"Card '{card.get('id')}' has unexpected language {card.get('language')!r}"
            )

    def test_no_en_entries_added(self):
        """No new English KB entries were added — count stays exactly 5."""
        _require_import()
        entries = load_knowledge(KB_PATH, include_pending=True)
        en_entries = [e for e in entries if e["language"] == "en"]
        assert len(en_entries) == 5, (
            f"Expected exactly 5 en KB entries, got {len(en_entries)}. No new English entries should be added."
        )

    def test_no_en_cards_added(self):
        """No new English cards were added — count stays exactly 5."""
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        en_cards = [c for c in cards if c.get("language") == "en"]
        assert len(en_cards) == 5, (
            f"Expected exactly 5 en cards, got {len(en_cards)}. No new English cards should be added."
        )


# ---------------------------------------------------------------------------
# Slice 4: Language eligibility — Swahili participant and matcher behavior
#
# The Jaccard matcher is English-centric (stemming/stopwords designed for EN).
# Swahili question routing via the existing matcher is a documented limitation.
# These tests characterize actual behavior without overclaiming accuracy.
# ---------------------------------------------------------------------------


def _make_staging_harness(kb_ids, language="sw"):
    """Build a staging NodeHarness with all 10 cards (pending included).

    include_pending=True is explicit synthetic staging: pending cards are baked
    with allow_pending=True so they are eligible at runtime.
    This is NEVER used on a production build.
    """
    _require_import()
    cards = load_answer_cards(CARDS_PATH, include_pending=True)
    source = render_answer_match(cards, include_pending=True)
    return NodeHarness(
        source,
        temp_state={"kb_ids": kb_ids, "kb_available": True},
        participant_data={
            "language_preference": language,
            "registration_complete": True,
        },
    )


class TestLanguageEligibilityWithSwCards:
    """Language selection/exclusion behavior after sw cards are added.

    The matcher enforces language_preference: a "sw" participant can only
    match sw-language cards, and an "en" participant can only match en-language
    cards. These tests verify the guard works for both directions.
    """

    def test_en_participant_english_question_still_routes_card(self):
        """English participant asking English question still routes en card after sw added."""
        _require_import()
        h = _make_staging_harness(ALL_KB_IDS, language="en")
        h.run("Why should I go to ANC?")
        assert h.temp_state["answer_route"] == "CARD"
        assert h.temp_state["matched_card"] == "anc_visits_en"

    def test_en_participant_cannot_match_sw_card(self):
        """English participant must NOT receive a sw card — language guard."""
        _require_import()
        h = _make_staging_harness(ALL_KB_IDS, language="en")
        h.run("Why should I go to ANC?")
        matched = h.temp_state.get("matched_card", "")
        assert not matched.endswith("_sw"), (
            f"English participant matched sw card {matched!r}; "
            "language guard must prevent sw card delivery to en participant."
        )

    def test_sw_participant_english_trigger_does_not_match_en_card(self):
        """sw participant asking English question must NOT match en card (language guard).

        Existing behavior preserved: TestLanguageEligibility.test_english_trigger_does_not_match_swahili_participant
        still passes; this is an independent counterpart assertion.
        """
        _require_import()
        h = _make_staging_harness(ALL_KB_IDS, language="sw")
        h.run("Why should I go to ANC?")
        assert h.temp_state["answer_route"] == "ASK_AI", (
            "sw participant must NOT match an en card even if the question text overlaps."
        )
        assert h.temp_state["matched_card"] == ""

    def test_sw_participant_unrelated_question_routes_ask_ai(self):
        """Unrelated/out-of-scope Swahili question must route ASK_AI (no wrong card)."""
        _require_import()
        h = _make_staging_harness(ALL_KB_IDS, language="sw")
        h.run("Nina maumivu ya kichwa")  # "I have a headache"
        assert h.temp_state["answer_route"] == "ASK_AI"
        assert h.temp_state["matched_card"] == ""

    def test_sw_participant_very_short_question_routes_ask_ai(self):
        """Very short Swahili input must not force any card (token guard)."""
        _require_import()
        h = _make_staging_harness(ALL_KB_IDS, language="sw")
        h.run("Habari")  # "Hello/News"
        assert h.temp_state["answer_route"] == "ASK_AI"

    def test_sw_participant_empty_input_routes_ask_ai(self):
        """Empty input from sw participant must route ASK_AI."""
        _require_import()
        h = _make_staging_harness(ALL_KB_IDS, language="sw")
        h.run("")
        assert h.temp_state["answer_route"] == "ASK_AI"


# ---------------------------------------------------------------------------
# Slice 5: Matcher behavior characterization for Swahili questions
#
# The Jaccard matcher is English-centric (stopwords, stemming designed for EN).
# These finite authored examples must match their expected Swahili cards.
# Swahili triggers are compared with Swahili questions; English-oriented word
# processing does not imply that every Swahili question must fall back.
#
# These cases are authored regression examples, not a held-out language
# evaluation. A missed expected match or wrong card fails these checks.
# ---------------------------------------------------------------------------


# Natural Swahili questions and expected topic cards.
# These are independently authored paraphrases — NOT copies of trigger strings.
# Format: (question, expected_card_id | None, notes)
# None = must NOT force any wrong card.
SWAHILI_AUTHORED_CHECK_CORPUS = [
    # In-scope: natural Swahili paraphrases of the five topics
    ("Kwa nini niende kliniki ya ujauzito?", "anc_visits_sw", "anc topic paraphrase"),
    ("Ni dalili zipi za hatari ninazopaswa kuangalia?", "danger_signs_sw", "danger signs paraphrase"),
    ("Nile chakula gani wakati wa ujauzito?", "food_groups_sw", "food groups paraphrase"),
    ("Ninywe maji kiasi gani kila siku nikiwa mjamzito?", "daily_care_sw", "daily care paraphrase"),
    ("Nitajiandaa vipi kwa ajili ya kujifungua?", "birth_plan_sw", "birth plan paraphrase"),
    # Out-of-scope: must NOT force any card
    ("Nina maumivu makali", None, "symptoms — no matching sw card"),
    ("Dawa gani ninywee?", None, "medicine — out of scope"),
    ("Mtoto wangu anasogea?", None, "fetal movement — not covered"),
]


class TestSwahiliMatcherBehavior:
    """Characterize sw question routing through the English-centric Jaccard matcher.

    LABEL: authored check corpus, same author as YAML.
    NOT held-out evidence. NOT a clinical recall or accuracy claim.
    Limitations are documented honestly. All sw content is pending draft.

    The word-processing rules are English-oriented, but Swahili trigger strings
    permit same-language word overlap. Passing these authored examples does not
    establish coverage of unseen questions, dialects or Sheng.
    """

    def _run(self, question, expected_id, language="sw"):
        h = _make_staging_harness(ALL_KB_IDS, language=language)
        result = h.run(question)
        route = h.temp_state["answer_route"]
        matched = h.temp_state.get("matched_card", "")
        if expected_id is not None:
            from ocs.answer_cards import load_answer_cards as load_cards

            cards = load_cards(CARDS_PATH, include_pending=True)
            expected = next(card for card in cards if card["id"] == expected_id)
            assert question not in expected["triggers"]
            assert route == "CARD"
            assert matched == expected_id
            assert result == expected["answer"]
            correct = route == "CARD" and matched == expected_id
            wrong_card = route == "CARD" and matched != expected_id
            missed = route == "ASK_AI"
        else:
            correct = route == "ASK_AI"
            wrong_card = route == "CARD"
            missed = False
        return correct, wrong_card, missed, route, matched

    def test_zero_wrong_cards_on_sw_out_of_scope(self):
        """Out-of-scope Swahili questions must NEVER produce a wrong card.

        This is a hard contract regardless of matcher accuracy limitations.
        Even with English-centric matching, no wrong card is acceptable.
        """
        _require_import()
        out_of_scope = [(q, e, n) for q, e, n in SWAHILI_AUTHORED_CHECK_CORPUS if e is None]
        failures = []
        for question, expected, notes in out_of_scope:
            ok, wrong_card, missed, route, matched = self._run(question, expected)
            if not ok:
                failures.append({"q": question, "notes": notes, "matched": matched})
        assert failures == [], f"Wrong-card rate > 0 on out-of-scope Swahili questions: {failures}"

    def test_sw_matcher_behavior_report(self):
        """Report and enforce each expected result in the finite authored corpus.

        This is regression coverage, not a population accuracy estimate.
        """
        _require_import()
        rows = []
        for question, expected, notes in SWAHILI_AUTHORED_CHECK_CORPUS:
            ok, wrong_card, missed, route, matched = self._run(question, expected)
            if expected is None:
                outcome = "correct" if ok else "wrong_card"
            else:
                outcome = "correct" if ok else ("wrong_card" if wrong_card else "missed_expected")
            rows.append(
                {
                    "q": question,
                    "expected": expected or "ASK_AI",
                    "got": matched or "ASK_AI",
                    "outcome": outcome,
                    "notes": notes,
                }
            )

        in_scope = [r for r in rows if r["expected"] != "ASK_AI"]

        in_correct = sum(1 for r in in_scope if r["outcome"] == "correct")
        in_missed = sum(1 for r in in_scope if r["outcome"] == "missed_expected")
        in_wrong = sum(1 for r in in_scope if r["outcome"] == "wrong_card")

        print("\n--- Swahili matcher behavior (authored check, NOT held-out evidence) ---")
        print(f"In-scope  ({len(in_scope)}): matched={in_correct}, missed={in_missed}, wrong_card={in_wrong}")
        print(
            "LIMITATION: finite authored examples with Swahili triggers; "
            "no held-out, fluent-language or clinical accuracy claim."
        )
        for r in rows:
            print(
                f"  [{r['outcome'].upper():18s}] {r['q']!r:50s} expected={r['expected']} got={r['got']} ({r['notes']})"
            )

        assert rows
        assert all(row["outcome"] == "correct" for row in rows), rows

    def test_sw_participant_wrong_topic_routes_ask_ai(self):
        """A Swahili question about a wrong/unrelated topic must not force a card."""
        _require_import()
        # "What medicines should I take?" in Swahili — out of scope
        h = _make_staging_harness(ALL_KB_IDS, language="sw")
        h.run("Dawa gani ninywee wakati wa ujauzito?")
        assert h.temp_state["answer_route"] == "ASK_AI"
        assert h.temp_state["matched_card"] == ""

    def test_sw_participant_uncertain_question_routes_ask_ai(self):
        """A vague/uncertain Swahili question must not force a wrong card."""
        _require_import()
        h = _make_staging_harness(ALL_KB_IDS, language="sw")
        h.run("Sijui")  # "I don't know"
        assert h.temp_state["answer_route"] == "ASK_AI"


# ---------------------------------------------------------------------------
# Slice 6: Production exclusion invariants (double-check at render level)
# ---------------------------------------------------------------------------


class TestBilingualProductionPresence:
    """sw and en content must be fully present in the default production build.

    Owner has approved all 10 starter KB entries and cards.
    These tests verify the approved filter correctly returns all 10 entries/cards.
    Pending-exclusion logic is verified separately via synthetic fixtures in
    test_bilingual_production_build.py::TestPendingExclusionSafety.
    """

    def test_sw_kb_entries_in_production_load(self):
        """KB production load (include_pending=False) returns 10 entries total (5 en + 5 sw)."""
        _require_import()
        entries = load_knowledge(KB_PATH)  # default: include_pending=False
        assert len(entries) == 10, (
            f"Expected 10 approved KB entries (5 en + 5 sw), got {len(entries)}: {[e['id'] for e in entries]}"
        )
        sw_entries = [e for e in entries if e["language"] == "sw"]
        assert len(sw_entries) == 5, f"Expected 5 sw KB entries in production load; got {len(sw_entries)}"

    def test_sw_cards_in_production_load(self):
        """Card production load (include_pending=False) returns 10 cards total (5 en + 5 sw)."""
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=False)
        card_ids = [c["id"] for c in cards]
        assert len(cards) == 10, f"Expected 10 approved cards (5 en + 5 sw), got {len(cards)}: {card_ids}"
        sw_cards = [c for c in cards if c.get("language") == "sw"]
        assert len(sw_cards) == 5, f"Expected 5 sw cards in production load; got {len(sw_cards)}"

    def test_sw_card_ids_present_in_production_render(self):
        """sw card IDs must appear in a production render (all approved)."""
        _require_import()
        cards = load_answer_cards(CARDS_PATH)  # approved only
        source = render_answer_match(cards)
        for sw_id in SW_CARD_IDS:
            assert sw_id in source, f"sw card ID '{sw_id}' missing from production render source."

    def test_en_card_ids_present_in_production_render(self):
        """en card IDs must appear in production render (all approved)."""
        _require_import()
        cards = load_answer_cards(CARDS_PATH)  # approved only
        source = render_answer_match(cards)
        for en_id in EN_CARD_IDS:
            assert en_id in source, f"en card ID '{en_id}' missing from production render source."
