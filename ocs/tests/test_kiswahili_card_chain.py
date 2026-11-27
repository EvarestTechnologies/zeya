"""Authored Kiswahili draft checks in the pinned local sandbox, not clinical evidence."""

from pathlib import Path

import pytest

from ocs.answer_cards import load_answer_cards, render_answer_match
from ocs.build_pipeline import build_pipeline
from ocs.knowledge import load_knowledge, render_kb_node
from ocs.output_policy import load_output_policy, render_output_guard
from ocs.tests.sandbox import NodeHarness

ROOT = Path(__file__).resolve().parents[2]
CASES = [
    ("anc_purpose_sw", "Kwa nini niende kliniki ya ujauzito?"),
    ("pregnancy_records_sw", "Nihifadhi rekodi zangu za ujauzito?"),
    ("food_variety_sw", "Nile chakula gani wakati wa ujauzito?"),
    ("food_safety_sw", "Chakula salama na safi kwa mjamzito ni muhimu?"),
    ("birth_preparation_sw", "Nijiandae vipi kwa kujifungua?"),
]


def corpus():
    return (
        load_knowledge(ROOT / "docs/zeya-knowledge-base.md", include_pending=True),
        load_answer_cards(ROOT / "docs/answer-cards.yaml", include_pending=True),
    )


@pytest.mark.parametrize("card_id,question", CASES, ids=[c[0] for c in CASES])
def test_kb_matcher_guard_delivers_exact_sw_answer(card_id, question):
    entries, cards = corpus()
    target = next(c for c in cards if c["id"] == card_id)
    entry = next(e for e in entries if e["id"] == target["kb_ref"] and e["language"] == "sw")
    assert target["answer"] == entry["text"]
    assert question not in target["triggers"]
    data = {"language_preference": "sw", "registration_complete": True}
    kb = NodeHarness(render_kb_node(entries, include_pending=True), participant_data=data)
    assert kb.run(question) == question
    assert kb.temp_state["kb_available"] is True
    assert target["kb_ref"] in kb.temp_state["kb_ids"]
    assert target["answer"] in kb.temp_state["kb_section"]
    for english in (e for e in entries if e["language"] == "en"):
        assert english["text"] not in kb.temp_state["kb_section"]
    matcher = NodeHarness(
        render_answer_match(cards, include_pending=True), temp_state=kb.temp_state, participant_data=data
    )
    answer = matcher.run(question)
    assert matcher.temp_state["answer_route"] == "CARD"
    assert matcher.temp_state["matched_card"] == card_id
    assert answer == target["answer"]
    guard = NodeHarness(
        render_output_guard(load_output_policy(str(ROOT / "docs/output-policy.json"))),
        temp_state=matcher.temp_state,
        participant_data=data,
    )
    assert guard.run(answer) == target["answer"]
    assert guard.temp_state["guard_route"] == "PASS"


def test_food_variety_draft_retains_whole_grain_qualifier():
    entries, cards = corpus()
    sw_entry = next(e for e in entries if e["id"] == "food_variety" and e["language"] == "sw")
    sw_card = next(c for c in cards if c["id"] == "food_variety_sw")
    assert "nafaka zisizokobolewa" in sw_entry["text"]
    assert sw_card["answer"] == sw_entry["text"]


def test_anc_draft_uses_attend_verb():
    entries, cards = corpus()
    entry = next(e for e in entries if e["id"] == "anc_purpose" and e["language"] == "sw")
    card = next(c for c in cards if c["id"] == "anc_purpose_sw")
    assert "na uhudhurie ziara wanazopendekeza" in entry["text"]
    assert card["answer"] == entry["text"]


def test_birth_preparation_triggers_use_prepare_wording():
    _, cards = corpus()
    card = next(c for c in cards if c["id"] == "birth_preparation_sw")
    assert "Nijiandaeje kwa kujifungua?" in card["triggers"]
    assert all("Nijijendeaje" not in trigger for trigger in card["triggers"])


@pytest.mark.parametrize("language", ["en", "sw"])
def test_actual_default_builder_excludes_pending_content(language):
    entries, cards = corpus()
    flow = build_pipeline(0, 0)
    nodes = {node["id"]: node["data"]["params"] for node in flow["data"]["nodes"]}
    data = {"language_preference": language, "registration_complete": True}
    kb = NodeHarness(nodes["kb_context"]["code"], participant_data=data)
    question = "Nijiandae vipi kwa kujifungua?" if language == "sw" else "How should I prepare for birth?"
    assert kb.run(question) == question
    assert kb.temp_state["kb_available"] is False
    assert kb.temp_state["kb_ids"] == []
    assert kb.temp_state["kb_section"] == ""
    matcher = NodeHarness(nodes["answer_match"]["code"], temp_state=kb.temp_state, participant_data=data)
    assert matcher.run(question) == question
    assert matcher.temp_state["answer_route"] == "ASK_AI"
    assert matcher.temp_state["matched_card"] == ""
    assert all(entry["review_status"] == "pending" for entry in entries)
    assert all(card["review_status"] == "pending" for card in cards)
