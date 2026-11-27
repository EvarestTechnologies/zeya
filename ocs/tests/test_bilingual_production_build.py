"""Production-default bilingual content and synthetic pending-exclusion checks."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
KB_PATH = ROOT / "docs" / "zeya-knowledge-base.md"
CARDS_PATH = ROOT / "docs" / "answer-cards.yaml"

FIVE_TOPIC_IDS = {
    "anc_purpose",
    "pregnancy_records",
    "food_variety",
    "food_safety",
    "birth_preparation",
}
EN_CARD_IDS = {f"{t}_en" for t in FIVE_TOPIC_IDS}
SW_CARD_IDS = {f"{t}_sw" for t in FIVE_TOPIC_IDS}

_import_exc = None
try:
    from ocs.answer_cards import load_answer_cards, render_answer_match
    from ocs.build_pipeline import build_pipeline
    from ocs.knowledge import load_knowledge, render_kb_node
    from ocs.tests.sandbox import NodeHarness

    _IMPORT_OK = True
except Exception as exc:
    _IMPORT_OK = False
    _import_exc = exc


def _require():
    if not _IMPORT_OK:
        pytest.fail(f"Import failed: {_import_exc!r}")


# ---------------------------------------------------------------------------
# 1. KB loader — production default (include_pending=False)
# ---------------------------------------------------------------------------


class TestProductionKBLoader:
    """Default load must return exactly 10 approved entries, 5 en + 5 sw."""

    def test_default_load_returns_10_entries(self):
        _require()
        entries = load_knowledge(KB_PATH)  # include_pending=False by default
        assert len(entries) == 10, (
            f"Expected 10 approved KB entries (5 en + 5 sw) from default production load; "
            f"got {len(entries)}.  "
            "All 10 entries must have Review-state: approved in docs/zeya-knowledge-base.md."
        )

    def test_default_load_all_entries_are_approved(self):
        _require()
        entries = load_knowledge(KB_PATH)
        not_approved = [e["id"] for e in entries if e["review_status"] != "approved"]
        assert not_approved == [], f"All production-loaded KB entries must be approved; pending found: {not_approved}"

    def test_default_load_has_5_english_entries(self):
        _require()
        entries = load_knowledge(KB_PATH)
        en = [e for e in entries if e["language"] == "en"]
        assert len(en) == 5, f"Expected exactly 5 en KB entries; got {len(en)}"

    def test_default_load_has_5_kiswahili_entries(self):
        _require()
        entries = load_knowledge(KB_PATH)
        sw = [e for e in entries if e["language"] == "sw"]
        assert len(sw) == 5, f"Expected exactly 5 sw KB entries; got {len(sw)}"

    def test_default_load_english_ids_are_exactly_the_five_topics(self):
        _require()
        entries = load_knowledge(KB_PATH)
        en_ids = {e["id"] for e in entries if e["language"] == "en"}
        assert en_ids == FIVE_TOPIC_IDS, f"en KB IDs mismatch: {en_ids}"

    def test_default_load_kiswahili_ids_are_exactly_the_five_topics(self):
        _require()
        entries = load_knowledge(KB_PATH)
        sw_ids = {e["id"] for e in entries if e["language"] == "sw"}
        assert sw_ids == FIVE_TOPIC_IDS, f"sw KB IDs mismatch: {sw_ids}"


# ---------------------------------------------------------------------------
# 2. Answer-card loader — production default (include_pending=False)
# ---------------------------------------------------------------------------


class TestProductionCardLoader:
    """Default load must return exactly 10 approved cards, 5 en + 5 sw."""

    def test_default_load_returns_10_cards(self):
        _require()
        cards = load_answer_cards(CARDS_PATH)  # include_pending=False by default
        assert len(cards) == 10, (
            f"Expected 10 approved cards (5 en + 5 sw) from default production load; "
            f"got {len(cards)}.  "
            'All 10 cards must have "review_status": "approved" in docs/answer-cards.yaml.'
        )

    def test_default_load_all_cards_are_approved(self):
        _require()
        cards = load_answer_cards(CARDS_PATH)
        not_approved = [c["id"] for c in cards if c["review_status"] != "approved"]
        assert not_approved == [], f"All production-loaded cards must be approved; pending found: {not_approved}"

    def test_default_load_has_5_english_cards(self):
        _require()
        cards = load_answer_cards(CARDS_PATH)
        en = [c for c in cards if c["language"] == "en"]
        assert len(en) == 5, f"Expected 5 en cards; got {len(en)}"

    def test_default_load_has_5_kiswahili_cards(self):
        _require()
        cards = load_answer_cards(CARDS_PATH)
        sw = [c for c in cards if c["language"] == "sw"]
        assert len(sw) == 5, f"Expected 5 sw cards; got {len(sw)}"

    def test_default_load_english_card_ids_are_exact(self):
        _require()
        cards = load_answer_cards(CARDS_PATH)
        en_ids = {c["id"] for c in cards if c["language"] == "en"}
        assert en_ids == EN_CARD_IDS, f"en card IDs mismatch: {en_ids}"

    def test_default_load_kiswahili_card_ids_are_exact(self):
        _require()
        cards = load_answer_cards(CARDS_PATH)
        sw_ids = {c["id"] for c in cards if c["language"] == "sw"}
        assert sw_ids == SW_CARD_IDS, f"sw card IDs mismatch: {sw_ids}"


# ---------------------------------------------------------------------------
# 3. Full production pipeline path — KB node → matcher → guard per language
# ---------------------------------------------------------------------------


class TestProductionPipelinePath:
    """Default build_pipeline (no include_pending) must deliver approved content."""

    def _node_code(self, node_name: str) -> str:
        flow = build_pipeline(0, 0)  # production default: include_pending=False
        return next(
            n["data"]["params"]["code"] for n in flow["data"]["nodes"] if n["data"]["params"]["name"] == node_name
        )

    def test_production_kb_node_sets_kb_available_true_for_english_participant(self):
        _require()
        kb_code = self._node_code("kb_context")
        h = NodeHarness(
            kb_code,
            participant_data={"language_preference": "en", "registration_complete": True},
        )
        h.run("Why should I go to ANC?")
        assert h.temp_state["kb_available"] is True, (
            "Production KB node must set kb_available=True for an English participant "
            "once approved entries exist.  Currently kb_available=False because all "
            "entries are pending."
        )

    def test_production_kb_node_sets_kb_available_true_for_swahili_participant(self):
        _require()
        kb_code = self._node_code("kb_context")
        h = NodeHarness(
            kb_code,
            participant_data={"language_preference": "sw", "registration_complete": True},
        )
        h.run("Kwa nini niende kliniki ya ujauzito?")
        assert h.temp_state["kb_available"] is True, (
            "Production KB node must set kb_available=True for a Swahili participant "
            "once approved entries exist.  Currently kb_available=False because all "
            "entries are pending."
        )

    def test_production_english_question_routes_card(self):
        _require()
        flow = build_pipeline(0, 0)
        nodes = {n["data"]["params"]["name"]: n["data"]["params"] for n in flow["data"]["nodes"]}
        data = {"language_preference": "en", "registration_complete": True}
        kb = NodeHarness(nodes["kb_context"]["code"], participant_data=data)
        question = "Why should I go to ANC?"
        kb.run(question)
        assert kb.temp_state["kb_available"] is True
        assert "anc_purpose" in kb.temp_state["kb_ids"]
        matcher = NodeHarness(nodes["answer_match"]["code"], temp_state=kb.temp_state, participant_data=data)
        matcher.run(question)
        assert matcher.temp_state["answer_route"] == "CARD"
        assert matcher.temp_state["matched_card"] == "anc_purpose_en"

    def test_production_kiswahili_question_routes_card(self):
        _require()
        flow = build_pipeline(0, 0)
        nodes = {n["data"]["params"]["name"]: n["data"]["params"] for n in flow["data"]["nodes"]}
        data = {"language_preference": "sw", "registration_complete": True}
        kb = NodeHarness(nodes["kb_context"]["code"], participant_data=data)
        question = "Kwa nini niende kliniki ya ujauzito?"
        kb.run(question)
        assert kb.temp_state["kb_available"] is True
        assert "anc_purpose" in kb.temp_state["kb_ids"]
        matcher = NodeHarness(nodes["answer_match"]["code"], temp_state=kb.temp_state, participant_data=data)
        matcher.run(question)
        assert matcher.temp_state["answer_route"] == "CARD"
        assert matcher.temp_state["matched_card"] == "anc_purpose_sw"

    def _assert_delivered_topic(self, language, topic_id):
        from ocs.answer_cards import load_answer_cards as load_cards
        from ocs.knowledge import load_knowledge as load_entries
        from ocs.tests.sandbox import NodeHarness as Harness

        cards = load_cards(CARDS_PATH)
        target = next(card for card in cards if card["id"] == f"{topic_id}_{language}")
        question = target["triggers"][0]
        data = {"language_preference": language, "registration_complete": True}
        kb = Harness(self._node_code("kb_context"), participant_data=data)
        assert kb.run(question) == question
        assert kb.temp_state["kb_available"] is True
        assert topic_id in kb.temp_state["kb_ids"]
        assert target["answer"] in kb.temp_state["kb_section"]
        for entry in load_entries(KB_PATH):
            if entry["language"] != language:
                assert entry["text"] not in kb.temp_state["kb_section"]
        matcher = Harness(self._node_code("answer_match"), temp_state=kb.temp_state, participant_data=data)
        answer = matcher.run(question)
        assert matcher.temp_state["answer_route"] == "CARD"
        assert matcher.temp_state["matched_card"] == target["id"]
        assert answer == target["answer"]
        guard = Harness(self._node_code("output_guard"), temp_state=matcher.temp_state, participant_data=data)
        assert guard.run(answer) == target["answer"]
        assert guard.temp_state["guard_route"] == "PASS"

    @pytest.mark.parametrize("topic_id", sorted(FIVE_TOPIC_IDS))
    def test_production_all_five_en_topics_are_in_kb_node(self, topic_id):
        self._assert_delivered_topic("en", topic_id)

    @pytest.mark.parametrize("topic_id", sorted(FIVE_TOPIC_IDS))
    def test_production_all_five_sw_topics_are_in_kb_node(self, topic_id):
        self._assert_delivered_topic("sw", topic_id)


# ---------------------------------------------------------------------------
# 4. Pending-exclusion safety (synthetic fixtures — NOT using real KB)
#
# These tests verify the pending-exclusion logic using SYNTHETIC data.
# They are independent of the real KB's review_status and must remain GREEN
# even after the real entries are approved.
# ---------------------------------------------------------------------------


SYNTHETIC_PENDING_KB_MD = """\
# Synthetic test KB

---

## synth_pending_en

Review-state: pending
Language: en
Topics: test
Min-week:
Max-week:
Source-refs: https://example.com/ref1

Synthetic pending English entry — must never reach production.

---

## synth_pending_sw

Review-state: pending
Language: sw
Topics: test
Min-week:
Max-week:
Source-refs: https://example.com/ref2

Maandishi ya majaribio yaliyosubiri — hayapaswi kufikia uzalishaji.
"""

SYNTHETIC_PENDING_CARDS = [
    {
        "id": "synth_pending_en",
        "review_status": "pending",
        "language": "en",
        "kb_ref": "synth_pending_en",
        "topic_anchors": ["test", "synthetic"],
        "triggers": ["What is a synthetic test?"],
        "answer": "Synthetic pending English card answer text.",
    },
    {
        "id": "synth_pending_sw",
        "review_status": "pending",
        "language": "sw",
        "kb_ref": "synth_pending_sw",
        "topic_anchors": ["majaribio"],
        "triggers": ["Nini majaribio ya synthetic?"],
        "answer": "Jibu la kadi ya majaribio ya Kiswahili iliyosubiri.",
    },
]


class TestPendingExclusionSafety:
    """Synthetic-fixture tests: pending entries must NEVER appear in production renders.

    These tests use EXPLICIT synthetic pending fixtures, not the real KB.
    They remain valid and GREEN regardless of the real KB's review_status.
    """

    def test_synthetic_pending_kb_excluded_by_default(self, tmp_path):
        _require()
        p = tmp_path / "kb.md"
        p.write_text(SYNTHETIC_PENDING_KB_MD, encoding="utf-8")
        entries = load_knowledge(p)  # include_pending=False
        assert entries == [], "Synthetic pending KB entries must be excluded from default (include_pending=False) load"

    def test_synthetic_pending_kb_included_with_flag(self, tmp_path):
        _require()
        p = tmp_path / "kb.md"
        p.write_text(SYNTHETIC_PENDING_KB_MD, encoding="utf-8")
        entries = load_knowledge(p, include_pending=True)
        assert len(entries) == 2
        assert all(e["review_status"] == "pending" for e in entries)

    def test_synthetic_pending_cards_excluded_by_default(self, tmp_path):
        _require()
        import json

        p = tmp_path / "cards.yaml"
        p.write_text(json.dumps(SYNTHETIC_PENDING_CARDS), encoding="utf-8")
        cards = load_answer_cards(p)  # include_pending=False
        assert cards == [], "Synthetic pending cards must be excluded from default (include_pending=False) load"

    def test_synthetic_pending_render_raises_for_raw_pending_cards(self):
        """render_answer_match rejects pending cards supplied without include_pending=True.

        This is the production safety guard: you cannot accidentally bake pending
        cards into the production render by forgetting to filter them first.
        The correct path is load_answer_cards(path) → approved-only list → render.
        """
        _require()
        import pytest as _pytest

        with _pytest.raises(ValueError, match="[Pp]ending"):
            render_answer_match(SYNTHETIC_PENDING_CARDS)  # must raise, not silently include

    def test_synthetic_approved_only_render_has_no_pending_ids(self, tmp_path):
        """Approved-only load → render contains no pending card IDs."""
        _require()
        import json

        p = tmp_path / "cards.yaml"
        p.write_text(json.dumps(SYNTHETIC_PENDING_CARDS), encoding="utf-8")
        approved_cards = load_answer_cards(p)  # include_pending=False → []
        assert approved_cards == []
        source = render_answer_match(approved_cards)  # empty list → no pending IDs
        for card in SYNTHETIC_PENDING_CARDS:
            assert card["id"] not in source, f"Pending card ID {card['id']!r} must not appear in approved-only render"

    def test_synthetic_pending_kb_node_has_empty_candidate_list(self, tmp_path):
        _require()
        p = tmp_path / "kb.md"
        p.write_text(SYNTHETIC_PENDING_KB_MD, encoding="utf-8")
        entries = load_knowledge(p)  # all pending → empty
        source = render_kb_node(entries)
        h = NodeHarness(
            source,
            participant_data={"language_preference": "en", "registration_complete": True},
        )
        h.run("synthetic test")
        assert h.temp_state["kb_available"] is False, (
            "KB node baked with 0 approved entries must set kb_available=False"
        )
        assert h.temp_state["kb_ids"] == []

    def test_synthetic_pending_render_allow_pending_true_includes_them(self):
        _require()
        source = render_answer_match(SYNTHETIC_PENDING_CARDS, include_pending=True)
        for card in SYNTHETIC_PENDING_CARDS:
            assert card["id"] in source, (
                f"Pending card {card['id']!r} must appear in staging render (include_pending=True)"
            )

    def test_synthetic_render_pending_does_not_relabel_as_approved(self):
        """include_pending=True must add eligible flag but never change review_status."""
        _require()
        render_answer_match(SYNTHETIC_PENDING_CARDS, include_pending=True)
        for card in SYNTHETIC_PENDING_CARDS:
            assert card["review_status"] == "pending", (
                f"render_answer_match must not mutate card {card['id']!r}'s review_status"
            )


# ---------------------------------------------------------------------------
# 5. Unknown / out-of-scope routing guard — production pipeline
# ---------------------------------------------------------------------------


class TestProductionKnowledgeGuard:
    """Unknown questions must still route ASK_AI via the knowledge guard."""

    def test_unknown_en_question_routes_ask_ai(self):
        _require()
        flow = build_pipeline(0, 0)
        nodes = {n["data"]["params"]["name"]: n["data"]["params"] for n in flow["data"]["nodes"]}
        data = {"language_preference": "en", "registration_complete": True}
        kb = NodeHarness(nodes["kb_context"]["code"], participant_data=data)
        question = "What is the weather today?"
        kb.run(question)
        matcher = NodeHarness(nodes["answer_match"]["code"], temp_state=kb.temp_state, participant_data=data)
        matcher.run(question)
        assert matcher.temp_state["answer_route"] == "ASK_AI"
        assert matcher.temp_state["matched_card"] == ""

    def test_unknown_sw_question_routes_ask_ai(self):
        _require()
        flow = build_pipeline(0, 0)
        nodes = {n["data"]["params"]["name"]: n["data"]["params"] for n in flow["data"]["nodes"]}
        data = {"language_preference": "sw", "registration_complete": True}
        kb = NodeHarness(nodes["kb_context"]["code"], participant_data=data)
        question = "Hali ya hewa leo ni nini?"
        kb.run(question)
        matcher = NodeHarness(nodes["answer_match"]["code"], temp_state=kb.temp_state, participant_data=data)
        matcher.run(question)
        assert matcher.temp_state["answer_route"] == "ASK_AI"
        assert matcher.temp_state["matched_card"] == ""
