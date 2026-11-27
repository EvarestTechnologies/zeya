"""Tests for ocs/answer_cards.py: load_answer_cards, validate_cards and render_answer_match.

Issue #23: answer-card loader and matcher (limited v0 starter, five English cards).
All cards are pending review; Kiswahili translations are explicitly follow-up work.

Repair-1 additions
------------------
TestLoadValidatesSchema     — behavioral REDs: load_answer_cards must validate before
                              returning cards; currently no validation → these tests fail.
TestRenderAnswerMatchEligibility — behavioral REDs: render_answer_match must reject
                              pending cards by default; currently no guard → these fail.
TestValidateCardsDirect     — skipped if validate_cards not yet importable; becomes
                              GREEN after implementation.
Existing TestRenderAnswerMatch call sites updated to render_answer_match(cards,
include_pending=True) so they remain correct after the eligibility guard is added.
"""

import json
import pathlib

import pytest

CARDS_PATH = pathlib.Path(__file__).resolve().parents[2] / "docs" / "answer-cards.yaml"

# ---------------------------------------------------------------------------
# Synthetic fixture — approved card for schema tests; NOT from the real YAML.
# review_status="approved" so schema tests can test approved-path separately.
# ---------------------------------------------------------------------------
_VALID_APPROVED_CARD: dict = {
    "id": "test_card_en",
    "review_status": "approved",
    "language": "en",
    "kb_ref": "anc_visits",
    "topic_anchors": ["anc", "antenatal"],
    "triggers": ["Why should I go to ANC?"],
    "answer": "Antenatal visits provide health care and support during pregnancy.",
}

# ---------------------------------------------------------------------------
# Import under test — raises ImportError / ModuleNotFoundError when missing,
# which is a collection error not a behavioural RED.  Wrapped so we get a
# single clear failure rather than a cascade.
# ---------------------------------------------------------------------------
_import_exc: Exception | None = None
_validate_cards_fn = None
try:
    from ocs.answer_cards import load_answer_cards, render_answer_match

    try:
        from ocs.answer_cards import validate_cards as _validate_cards_fn
    except ImportError:
        pass  # validate_cards not yet implemented; direct tests will skip
    _IMPORT_OK = True
except Exception as _exc:  # noqa: BLE001
    _IMPORT_OK = False
    _import_exc = _exc


def _require_import():
    if not _IMPORT_OK:
        pytest.fail(f"Cannot import ocs.answer_cards: {_import_exc!r}")


def _write_cards_file(tmp_path, cards):
    """Write a JSON-format cards file for schema tests."""
    p = tmp_path / "cards.yaml"
    p.write_text(json.dumps(cards), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# load_answer_cards — baseline behaviour
# ---------------------------------------------------------------------------


class TestLoadAnswerCards:
    def test_loads_all_ten_starter_cards_when_include_pending(self):
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        assert len(cards) == 10, f"Expected 10 starter cards (5 en + 5 sw), got {len(cards)}"

    def test_returns_10_approved_cards_by_default(self):
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=False)
        assert len(cards) == 10, f"Default (include_pending=False) must return 10 approved cards; got {len(cards)}"
        for card in cards:
            assert card["review_status"] == "approved", (
                f"Card {card['id']!r} returned by default load must be approved; got {card['review_status']!r}"
            )

    def test_each_card_has_required_keys(self):
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        required = {"id", "review_status", "language", "kb_ref", "triggers", "answer"}
        for card in cards:
            missing = required - card.keys()
            assert not missing, f"Card {card.get('id')!r} missing keys: {missing}"

    def test_english_starter_cards_are_english(self):
        """The five English starter cards must have language='en'."""
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        en_cards = [c for c in cards if c.get("language") == "en"]
        assert len(en_cards) == 5, f"Expected exactly 5 en cards, got {len(en_cards)}"
        for card in en_cards:
            assert card["language"] == "en", (
                f"Card {card.get('id')!r} classified as en but language={card.get('language')!r}"
            )

    def test_swahili_starter_cards_are_sw_and_approved(self):
        """The five Kiswahili starter cards must have language='sw' and review_status='approved'.

        Owner has approved the Kiswahili starter pack for production eligibility.
        review_status='approved' denotes owner content eligibility; it is not a
        clinician certification claim.  No clinical validation is claimed.
        """
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        sw_cards = [c for c in cards if c.get("language") == "sw"]
        assert len(sw_cards) == 5, f"Expected exactly 5 sw cards, got {len(sw_cards)}"
        for card in sw_cards:
            assert card["language"] == "sw"
            assert card["review_status"] == "approved", (
                f"sw card {card.get('id')!r} must be approved — owner has approved the Kiswahili starter pack"
            )

    def test_all_starter_cards_are_approved(self):
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        not_approved = [c["id"] for c in cards if c.get("review_status") != "approved"]
        assert not_approved == [], f"Expected all approved, found non-approved: {not_approved}"

    def test_card_ids_are_stable_and_unique(self):
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        ids = [c["id"] for c in cards]
        assert len(ids) == len(set(ids)), f"Duplicate card IDs: {ids}"

    def test_expected_kb_refs(self):
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        kb_refs = {c["kb_ref"] for c in cards}
        expected = {
            "anc_visits",
            "danger_signs",
            "food_groups",
            "daily_care",
            "birth_plan",
        }
        assert kb_refs == expected, f"KB refs mismatch: got {kb_refs}"

    def test_answers_under_80_words(self):
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        for card in cards:
            word_count = len(card["answer"].split())
            assert word_count <= 80, f"Card {card['id']!r} answer has {word_count} words (limit 80): {card['answer']!r}"

    def test_triggers_non_empty_list_per_card(self):
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        for card in cards:
            assert isinstance(card["triggers"], list), f"Card {card['id']!r} triggers is not a list"
            assert len(card["triggers"]) >= 1, f"Card {card['id']!r} has no triggers"

    def test_trigger_strings_non_empty(self):
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        for card in cards:
            for trigger in card["triggers"]:
                assert isinstance(trigger, str) and trigger.strip(), (
                    f"Card {card['id']!r} has empty trigger: {trigger!r}"
                )


# ---------------------------------------------------------------------------
# TestLoadValidatesSchema — BEHAVIORAL REDs against current implementation.
#
# Each test passes malformed data through load_answer_cards and expects
# ValueError.  Current impl does no validation; these tests FAIL (RED) until
# the fix adds validate_cards() and wires it into load_answer_cards().
# ---------------------------------------------------------------------------


class TestLoadValidatesSchema:
    """Behavioral RED tests: load_answer_cards must validate before returning."""

    def test_raises_on_non_list_file(self, tmp_path):
        """File root must be a JSON array; a JSON object must raise ValueError."""
        _require_import()
        path = _write_cards_file(tmp_path, {"not": "a list"})
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_non_dict_element(self, tmp_path):
        """Each array element must be a JSON object; a bare string must raise."""
        _require_import()
        path = _write_cards_file(tmp_path, ["not_a_dict"])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_missing_required_key(self, tmp_path):
        """Card without 'kb_ref' must raise ValueError."""
        _require_import()
        card = {k: v for k, v in _VALID_APPROVED_CARD.items() if k != "kb_ref"}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_empty_id(self, tmp_path):
        """Card with id='' must raise ValueError."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "id": ""}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_whitespace_only_id(self, tmp_path):
        """Card with id='   ' must raise ValueError."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "id": "   "}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_malformed_review_status(self, tmp_path):
        """review_status='approved_draft' is not a known status; must raise ValueError."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "review_status": "approved_draft"}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_uppercase_approved(self, tmp_path):
        """'APPROVED' is not equal to 'approved'; must raise ValueError."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "review_status": "APPROVED"}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_unsupported_language(self, tmp_path):
        """language='fr' is not a supported language; must raise ValueError."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "language": "fr"}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_empty_language(self, tmp_path):
        """language='' is not a supported language; must raise ValueError."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "language": ""}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_empty_kb_ref(self, tmp_path):
        """kb_ref='' must raise ValueError."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "kb_ref": ""}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_empty_triggers_list(self, tmp_path):
        """triggers=[] must raise ValueError."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "triggers": []}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_non_string_trigger(self, tmp_path):
        """triggers=[123] (non-string element) must raise ValueError."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "triggers": [123]}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises((ValueError, TypeError)):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_empty_string_trigger(self, tmp_path):
        """triggers=[''] (empty string element) must raise ValueError."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "triggers": [""]}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_empty_answer(self, tmp_path):
        """answer='' must raise ValueError."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "answer": ""}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_over_80_words_answer(self, tmp_path):
        """Answer with 81 words must raise ValueError."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "answer": " ".join(["word"] * 81)}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_duplicate_id_language(self, tmp_path):
        """Two cards with same (id, language) must raise ValueError."""
        _require_import()
        path = _write_cards_file(tmp_path, [_VALID_APPROVED_CARD, _VALID_APPROVED_CARD])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_validates_pending_cards_even_when_not_included(self, tmp_path):
        """Malformed pending card must be caught even when include_pending=False."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "review_status": "pending", "id": ""}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=False)

    def test_valid_approved_card_loads_without_error(self, tmp_path):
        """Sanity: a well-formed approved card must load without error."""
        _require_import()
        path = _write_cards_file(tmp_path, [_VALID_APPROVED_CARD])
        cards = load_answer_cards(path, include_pending=False)
        assert len(cards) == 1
        assert cards[0]["id"] == "test_card_en"

    def test_valid_pending_card_loads_with_include_pending(self, tmp_path):
        """Sanity: a well-formed pending card loads when include_pending=True."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "review_status": "pending"}
        path = _write_cards_file(tmp_path, [card])
        cards = load_answer_cards(path, include_pending=True)
        assert len(cards) == 1


# ---------------------------------------------------------------------------
# TestRenderAnswerMatchEligibility — BEHAVIORAL REDs against current impl.
#
# render_answer_match(pending_cards) must raise ValueError by default.
# Current impl has no include_pending param and no guard → these fail (RED).
# ---------------------------------------------------------------------------


class TestRenderAnswerMatchEligibility:
    """Behavioral RED tests: render eligibility guard for pending cards."""

    def test_raises_on_pending_cards_by_default(self, tmp_path):
        """render_answer_match(pending_cards) must raise ValueError by default.

        Uses synthetic pending fixture — independent of real KB review_status.
        The safety guard: pending cards cannot reach production render accidentally.
        """
        _require_import()
        # Use synthetic pending fixture so this test stays valid regardless of real KB state.
        synthetic_pending = [
            {
                **_VALID_APPROVED_CARD,
                "id": "synth_pending_guard_test",
                "review_status": "pending",
            }
        ]
        path = _write_cards_file(tmp_path, synthetic_pending)
        pending_cards = load_answer_cards(path, include_pending=True)
        assert len(pending_cards) > 0, "Need pending cards to run this test"
        with pytest.raises(ValueError):
            render_answer_match(pending_cards)

    def test_allows_pending_cards_explicit_staging(self):
        """render_answer_match(cards, include_pending=True) must succeed for staging.

        Current impl has no include_pending kwarg → TypeError → RED.
        After repair: kwarg accepted, returns source string → GREEN.
        """
        _require_import()
        pending_cards = load_answer_cards(CARDS_PATH, include_pending=True)
        source = render_answer_match(pending_cards, include_pending=True)
        assert isinstance(source, str)
        assert "def main(input" in source

    def test_allows_approved_cards_by_default(self, tmp_path):
        """Approved cards must render without include_pending=True."""
        _require_import()
        from ocs.tests.sandbox import NodeHarness

        path = _write_cards_file(tmp_path, [_VALID_APPROVED_CARD])
        approved = load_answer_cards(path, include_pending=False)
        source = render_answer_match(approved)
        h = NodeHarness(
            source,
            temp_state={"kb_ids": ["anc_visits"], "kb_available": True},
            participant_data={"language_preference": "en"},
        )
        h.run("Why should I go to ANC?")
        assert h.temp_state["answer_route"] == "CARD"

    def test_rendered_baked_data_contains_allow_pending_flag(self, tmp_path):
        """Baked JSON must contain allow_pending key for independent runtime check.

        Current impl embeds bare array; this test fails (RED) until baked structure
        changes to {'cards': [...], 'allow_pending': bool}.
        """
        _require_import()

        path = _write_cards_file(tmp_path, [_VALID_APPROVED_CARD])
        approved = load_answer_cards(path, include_pending=False)
        source = render_answer_match(approved)
        # The baked JSON is double-encoded in the source; extract the outer literal.
        # Look for the string that was placed as the replacement of the placeholder.
        # It is a JSON string in the Python source: "\"[...]\"" → parse it.
        from ocs.answer_cards import PLACEHOLDER_LITERAL

        assert PLACEHOLDER_LITERAL not in source, "Placeholder was not replaced"
        # The baked data must have an 'allow_pending' key when decoded.
        # Find the replacement value in the source: it appears as a JSON-encoded string.
        # We locate it by searching for allow_pending in the source text.
        assert "allow_pending" in source, (
            "Baked source must contain 'allow_pending' for independent runtime check; "
            "current impl embeds a bare card array without this key."
        )


# ---------------------------------------------------------------------------
# TestRenderAnswerMatch — updated call sites use include_pending=True.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("flag", [None, 0, 1, "false", [], {}])
def test_loader_requires_explicit_boolean_pending_flag(flag):
    _require_import()
    with pytest.raises(TypeError, match="include_pending"):
        load_answer_cards(CARDS_PATH, include_pending=flag)


class TestRenderAnswerMatch:
    def test_render_returns_string(self):
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        source = render_answer_match(cards, include_pending=True)
        assert isinstance(source, str)

    def test_rendered_source_has_main_function(self):
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        source = render_answer_match(cards, include_pending=True)
        assert "def main(input" in source

    def test_rendered_source_has_no_placeholder(self):
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        source = render_answer_match(cards, include_pending=True)
        from ocs.answer_cards import PLACEHOLDER_LITERAL

        assert PLACEHOLDER_LITERAL not in source, (
            f"Placeholder literal {PLACEHOLDER_LITERAL!r} still present after rendering"
        )

    def test_rendered_source_contains_all_card_ids(self):
        _require_import()
        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        source = render_answer_match(cards, include_pending=True)
        for card in cards:
            assert card["id"] in source, f"Card ID {card['id']!r} not found in rendered source"

    def test_render_empty_cards_valid_and_routes_ask_ai(self):
        """Empty card list must still produce valid RestrictedPython that routes ASK_AI."""
        _require_import()
        from ocs.tests.sandbox import NodeHarness

        source = render_answer_match([])
        harness = NodeHarness(
            source,
            temp_state={"kb_ids": ["anc_visits"], "kb_available": True},
            participant_data={"language_preference": "en"},
        )
        result = harness.run("Why should I go to ANC?")
        assert result == "Why should I go to ANC?"
        assert harness.temp_state["answer_route"] == "ASK_AI"

    def test_rendered_source_is_valid_restricted_python(self):
        """render_answer_match output must pass the OCS CodeNode validator."""
        _require_import()
        from ocs.tests.sandbox import NodeHarness

        cards = load_answer_cards(CARDS_PATH, include_pending=True)
        source = render_answer_match(cards, include_pending=True)
        harness = NodeHarness(source)
        assert harness is not None


# ---------------------------------------------------------------------------
# TestValidateCardsDirect — skipped if validate_cards not yet importable.
# Becomes GREEN after implementation.  Tests the public validate_cards API.
# ---------------------------------------------------------------------------


class TestValidateCardsDirect:
    @staticmethod
    def _skip_if_unavailable():
        if _validate_cards_fn is None:
            pytest.skip("validate_cards not yet importable; run after repair implementation")

    def test_raises_on_non_list(self):
        self._skip_if_unavailable()
        with pytest.raises(ValueError, match="array"):
            _validate_cards_fn({"not": "a list"})

    def test_raises_on_non_dict_element(self):
        self._skip_if_unavailable()
        with pytest.raises(ValueError):
            _validate_cards_fn(["a_string_not_a_dict"])

    def test_raises_on_malformed_review_status(self):
        self._skip_if_unavailable()
        card = {**_VALID_APPROVED_CARD, "review_status": "in_review"}
        with pytest.raises(ValueError, match="review_status"):
            _validate_cards_fn([card])

    def test_raises_on_unsupported_language(self):
        self._skip_if_unavailable()
        card = {**_VALID_APPROVED_CARD, "language": "de"}
        with pytest.raises(ValueError, match="language"):
            _validate_cards_fn([card])

    def test_raises_on_over_80_words(self):
        self._skip_if_unavailable()
        card = {**_VALID_APPROVED_CARD, "answer": " ".join(["w"] * 81)}
        with pytest.raises(ValueError, match="80"):
            _validate_cards_fn([card])

    def test_raises_on_duplicate_id_language(self):
        self._skip_if_unavailable()
        with pytest.raises(ValueError, match="[Dd]uplicate"):
            _validate_cards_fn([_VALID_APPROVED_CARD, _VALID_APPROVED_CARD])

    def test_raises_on_exactly_80_words_in_validate_direct(self):
        self._skip_if_unavailable()
        card = {**_VALID_APPROVED_CARD, "answer": " ".join(["w"] * 80)}
        with pytest.raises(ValueError, match="80"):
            _validate_cards_fn([card])

    def test_valid_card_does_not_raise(self):
        self._skip_if_unavailable()
        _validate_cards_fn([_VALID_APPROVED_CARD])  # must not raise


# ---------------------------------------------------------------------------
# Repair-2 RED tests added against findings from parent-card-return-and-scope-red.log
# ---------------------------------------------------------------------------


class TestLoadValidatesSchemaRepair2:
    """Repair-2 schema RED tests: boundary, type safety, and slug validation."""

    def test_raises_on_exactly_80_words_answer(self, tmp_path):
        """<80 words is strict; exactly 80 words must raise ValueError.

        Current impl uses > 80 (accepts 80); this test fails (RED) until >= 80.
        """
        _require_import()
        card = {**_VALID_APPROVED_CARD, "answer": " ".join(["word"] * 80)}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_accepts_79_words_answer(self, tmp_path):
        """79 words is strictly < 80; must load without error."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "answer": " ".join(["word"] * 79)}
        path = _write_cards_file(tmp_path, [card])
        cards = load_answer_cards(path, include_pending=False)
        assert len(cards) == 1

    def test_raises_on_unhashable_review_status(self, tmp_path):
        """review_status=[1,2] is unhashable; must raise controlled ValueError, not TypeError.

        Current impl does not validate type before frozenset lookup -> TypeError.
        After repair: type check first -> ValueError.
        """
        _require_import()
        card = {**_VALID_APPROVED_CARD, "review_status": [1, 2]}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_unhashable_language(self, tmp_path):
        """language={'en': True} is unhashable; must raise controlled ValueError, not TypeError."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "language": {"en": True}}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_unsafe_slug_id(self, tmp_path):
        """Card id with spaces ('My Card') is not a safe slug; must raise ValueError.

        Current impl only checks non-empty; does not validate slug format.
        After repair: slug regex applied -> ValueError.
        """
        _require_import()
        card = {**_VALID_APPROVED_CARD, "id": "My Card With Spaces"}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_uppercase_in_id(self, tmp_path):
        """Uppercase in id ('ANC_Purpose_EN') is not a safe lowercase slug."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "id": "ANC_Purpose_EN"}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_valid_slug_id_loads_fine(self, tmp_path):
        """Sanity: lowercase slugs like 'anc_visits_en' must load without error."""
        _require_import()
        path = _write_cards_file(tmp_path, [_VALID_APPROVED_CARD])
        cards = load_answer_cards(path, include_pending=False)
        assert len(cards) == 1 and cards[0]["id"] == "test_card_en"


class TestRenderAnswerMatchBoolGuard:
    """render_answer_match include_pending must be strict bool.

    Current impl treats any truthy value as True; after repair TypeError for non-bool.
    """

    def test_raises_on_int_one_include_pending(self, tmp_path):
        """include_pending=1 (truthy int, not bool) must raise ValueError/TypeError.

        Current impl: 1 is truthy -> renders normally.
        After repair: isinstance check rejects non-bool -> raises.
        """
        _require_import()
        path = _write_cards_file(tmp_path, [_VALID_APPROVED_CARD])
        approved = load_answer_cards(path, include_pending=False)
        with pytest.raises((ValueError, TypeError)):
            render_answer_match(approved, include_pending=1)

    def test_raises_on_none_include_pending(self, tmp_path):
        """include_pending=None must raise ValueError/TypeError."""
        _require_import()
        path = _write_cards_file(tmp_path, [_VALID_APPROVED_CARD])
        approved = load_answer_cards(path, include_pending=False)
        with pytest.raises((ValueError, TypeError)):
            render_answer_match(approved, include_pending=None)

    def test_accepts_bool_false_default(self, tmp_path):
        """include_pending=False (default bool) must work for approved cards."""
        _require_import()
        path = _write_cards_file(tmp_path, [_VALID_APPROVED_CARD])
        approved = load_answer_cards(path, include_pending=False)
        source = render_answer_match(approved, include_pending=False)
        assert isinstance(source, str)

    def test_accepts_bool_true_explicit(self):
        """include_pending=True (bool) must work for staging."""
        _require_import()
        pending_cards = load_answer_cards(CARDS_PATH, include_pending=True)
        source = render_answer_match(pending_cards, include_pending=True)
        assert isinstance(source, str)


# ---------------------------------------------------------------------------
# Design-reset RED tests: topic_anchors validation
#
# topic_anchors is a new required field per the approved design reset.
# These tests fail on the current implementation (no topic_anchors validation)
# and go GREEN after the fix.
# ---------------------------------------------------------------------------


class TestTopicAnchorsDesignReset:
    """RED tests: validate_cards must enforce topic_anchors.

    Current impl: topic_anchors field is unknown; missing field passes silently.
    After fix: added to _REQUIRED_KEYS + validated → missing/malformed raises.
    """

    def test_raises_on_missing_topic_anchors(self, tmp_path):
        """Card without topic_anchors must raise ValueError.

        Current: missing field passes silently.
        After fix: topic_anchors in _REQUIRED_KEYS → raises ValueError.
        """
        _require_import()
        # Explicitly strip topic_anchors from the otherwise-valid fixture
        card = {k: v for k, v in _VALID_APPROVED_CARD.items() if k != "topic_anchors"}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_empty_topic_anchors_list(self, tmp_path):
        """topic_anchors=[] must raise ValueError."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "topic_anchors": []}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_non_string_anchor_element(self, tmp_path):
        """topic_anchors=[123] (non-string element) must raise ValueError/TypeError."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "topic_anchors": [123]}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises((ValueError, TypeError)):
            load_answer_cards(path, include_pending=True)

    def test_raises_on_empty_string_anchor(self, tmp_path):
        """topic_anchors=[''] (empty string element) must raise ValueError."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "topic_anchors": [""]}
        path = _write_cards_file(tmp_path, [card])
        with pytest.raises(ValueError):
            load_answer_cards(path, include_pending=True)

    def test_valid_topic_anchors_load_without_error(self, tmp_path):
        """Sanity: a card with valid topic_anchors must load without error (GREEN after fix)."""
        _require_import()
        card = {**_VALID_APPROVED_CARD, "topic_anchors": ["anc", "antenatal"]}
        path = _write_cards_file(tmp_path, [card])
        cards = load_answer_cards(path, include_pending=False)
        assert len(cards) == 1
        assert cards[0]["topic_anchors"] == ["anc", "antenatal"]
