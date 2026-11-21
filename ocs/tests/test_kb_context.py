"""Tests for ocs/nodes/kb_context.py via NodeHarness.

Synthetic approved fixtures are used for all selection-path tests.
Real KB entries are all pending; the node with its default '[]' placeholder
always produces kb_available=False, which is verified here.
"""

import datetime
import json
from pathlib import Path

from ocs.tests.sandbox import NodeHarness

KB_CONTEXT_PATH = Path(__file__).resolve().parents[2] / "ocs" / "nodes" / "kb_context.py"


def _node_source() -> str:
    return KB_CONTEXT_PATH.read_text(encoding="utf-8")


def _source_with_fixture(entries: list) -> str:
    """Substitute the empty KB JSON placeholder with synthetic test entries.

    The node embeds ``_KB_JSON = '[]'`` as its placeholder. This helper
    replaces that exact literal with a JSON-encoded list of synthetic entries
    so that selection-path tests can exercise approved-entry logic without
    labelling real draft entries as clinically approved.
    """
    source = _node_source()
    fixture_json = json.dumps(entries)
    patched = source.replace('KB_JSON = "[]"', "KB_JSON = " + repr(fixture_json), 1)
    assert patched != source, "Placeholder not found in node source — cannot inject fixture"
    return patched


# ---------------------------------------------------------------------------
# Synthetic approved fixtures — never label real draft entries as approved.
# ---------------------------------------------------------------------------

SYNTHETIC_ENTRIES = [
    {
        "id": "synth_en_a",
        "review_status": "approved",
        "language": "en",
        "text": "Approved English text A.",
        "source_refs": ["https://example.com"],
        "topics": ["test"],
        "min_week": None,
        "max_week": None,
    },
    {
        "id": "synth_en_b",
        "review_status": "approved",
        "language": "en",
        "text": "Approved English text B.",
        "source_refs": ["https://example.com"],
        "topics": ["test"],
        "min_week": None,
        "max_week": None,
    },
    {
        "id": "synth_sw_a",
        "review_status": "approved",
        "language": "sw",
        "text": "Maandishi ya Kiswahili yaliyoidhinishwa.",
        "source_refs": ["https://example.com"],
        "topics": ["test"],
        "min_week": None,
        "max_week": None,
    },
    {
        "id": "synth_pending",
        "review_status": "pending",
        "language": "en",
        "text": "Pending text that must be excluded.",
        "source_refs": [],
        "topics": [],
        "min_week": None,
        "max_week": None,
    },
    {
        "id": "synth_week",
        "review_status": "approved",
        "language": "en",
        "text": "Week-ranged approved text.",
        "source_refs": [],
        "topics": [],
        "min_week": 28,
        "max_week": 40,
    },
]


# ---------------------------------------------------------------------------
# Node outputs structure
# ---------------------------------------------------------------------------


def test_node_returns_input_unchanged():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source)
    result = harness.run("test message")
    assert result == "test message"


def test_node_writes_kb_section_key():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "kb_section" in harness.temp_state


def test_node_writes_kb_ids_key():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "kb_ids" in harness.temp_state


def test_node_writes_kb_available_key():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "kb_available" in harness.temp_state


def test_node_kb_ids_is_list():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert isinstance(harness.temp_state["kb_ids"], list)


def test_node_kb_available_is_bool():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert isinstance(harness.temp_state["kb_available"], bool)


def test_node_kb_section_is_string():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert isinstance(harness.temp_state["kb_section"], str)


# ---------------------------------------------------------------------------
# No approved content → fail closed (default placeholder is empty list)
# ---------------------------------------------------------------------------


def test_node_default_placeholder_produces_false():
    # Node ships with _KB_JSON = '[]' (empty); kb_available must be False.
    harness = NodeHarness(_node_source(), participant_data={"language_preference": "en"})
    harness.run("test")
    assert harness.temp_state["kb_available"] is False


def test_node_default_placeholder_produces_empty_section():
    harness = NodeHarness(_node_source(), participant_data={"language_preference": "en"})
    harness.run("test")
    assert harness.temp_state["kb_section"] == ""


def test_node_default_placeholder_produces_empty_ids():
    harness = NodeHarness(_node_source(), participant_data={"language_preference": "en"})
    harness.run("test")
    assert harness.temp_state["kb_ids"] == []


def test_node_pending_entries_produce_false():
    # Insert only pending entries; must still fail closed.
    pending_only = [dict(e) for e in SYNTHETIC_ENTRIES if e["review_status"] == "pending"]
    source = _source_with_fixture(pending_only)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert harness.temp_state["kb_available"] is False
    assert harness.temp_state["kb_ids"] == []


# ---------------------------------------------------------------------------
# Approved-entry selection
# ---------------------------------------------------------------------------


def test_node_approved_en_entries_selected_for_en_participant():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert harness.temp_state["kb_available"] is True
    assert "synth_en_a" in harness.temp_state["kb_ids"]
    assert "synth_en_b" in harness.temp_state["kb_ids"]


def test_node_pending_entry_excluded_even_in_fixture():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "synth_pending" not in harness.temp_state["kb_ids"]


def test_node_pending_text_absent_from_section():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "Pending text" not in harness.temp_state["kb_section"]


def test_node_section_contains_approved_english_texts():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    section = harness.temp_state["kb_section"]
    assert "Approved English text A." in section
    assert "Approved English text B." in section


# ---------------------------------------------------------------------------
# Language filtering
# ---------------------------------------------------------------------------


def test_node_selects_sw_entries_for_sw_participant():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language_preference": "sw"})
    harness.run("test")
    assert "synth_sw_a" in harness.temp_state["kb_ids"]
    assert "synth_en_a" not in harness.temp_state["kb_ids"]


def test_node_excludes_sw_entries_for_en_participant():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "synth_sw_a" not in harness.temp_state["kb_ids"]


def test_node_sw_text_absent_from_section_for_en_participant():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "Maandishi" not in harness.temp_state["kb_section"]


def test_node_defaults_to_en_when_language_not_saved():
    # Repair-1: absent language_preference must NOT silently default to 'en'.
    # (Covered more explicitly by test_node_absent_language_preference_produces_no_match.)
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={})
    harness.run("test")
    assert harness.temp_state["kb_available"] is False


def test_node_sw_entries_absent_when_no_language_saved():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={})
    harness.run("test")
    assert "synth_sw_a" not in harness.temp_state["kb_ids"]


# ---------------------------------------------------------------------------
# Week filtering
# ---------------------------------------------------------------------------


def test_node_includes_week_entry_within_range():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    # ga=29, enrolled 10 days ago (1 week) → week 30 → in range 28-40.
    harness = NodeHarness(
        source,
        participant_data={
            "language_preference": "en",
            "gestational_age_at_enrollment": 29,
            "enrolled_at": _ENROLLED_AT,
        },
        now=_NOW,
    )
    harness.run("test")
    assert "synth_week" in harness.temp_state["kb_ids"]


def test_node_excludes_week_entry_before_min():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    # ga=19, enrolled 10 days ago (1 week) → week 20 → below min_week=28.
    harness = NodeHarness(
        source,
        participant_data={
            "language_preference": "en",
            "gestational_age_at_enrollment": 19,
            "enrolled_at": _ENROLLED_AT,
        },
        now=_NOW,
    )
    harness.run("test")
    assert "synth_week" not in harness.temp_state["kb_ids"]


def test_node_excludes_week_entry_after_max():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    # ga=40, enrolled 10 days ago (1 week) → week 41 → above max_week=40.
    harness = NodeHarness(
        source,
        participant_data={
            "language_preference": "en",
            "gestational_age_at_enrollment": 40,
            "enrolled_at": _ENROLLED_AT,
        },
        now=_NOW,
    )
    harness.run("test")
    assert "synth_week" not in harness.temp_state["kb_ids"]


def test_node_includes_week_entry_when_current_week_absent():
    # Repair-1: unknown week → ranged entries EXCLUDED (not included).
    # (Covered explicitly by test_node_excludes_ranged_entries_when_week_unknown.)
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "synth_week" not in harness.temp_state["kb_ids"]


def test_node_includes_entry_at_exact_min_boundary():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    # ga=27, enrolled 10 days ago (1 week) → week 28 → exactly at min_week=28.
    harness = NodeHarness(
        source,
        participant_data={
            "language_preference": "en",
            "gestational_age_at_enrollment": 27,
            "enrolled_at": _ENROLLED_AT,
        },
        now=_NOW,
    )
    harness.run("test")
    assert "synth_week" in harness.temp_state["kb_ids"]


def test_node_includes_entry_at_exact_max_boundary():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    # ga=39, enrolled 10 days ago (1 week) → week 40 → exactly at max_week=40.
    harness = NodeHarness(
        source,
        participant_data={
            "language_preference": "en",
            "gestational_age_at_enrollment": 39,
            "enrolled_at": _ENROLLED_AT,
        },
        now=_NOW,
    )
    harness.run("test")
    assert "synth_week" in harness.temp_state["kb_ids"]


# ---------------------------------------------------------------------------
# Participant data integrity — must not be mutated
# ---------------------------------------------------------------------------


def test_node_does_not_mutate_existing_participant_keys():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    original = {
        "language_preference": "en",
        "gestational_age_at_enrollment": 29,
        "enrolled_at": _ENROLLED_AT,
        "name": "Test",
    }
    harness = NodeHarness(source, participant_data=dict(original), now=_NOW)
    harness.run("test")
    for key, val in original.items():
        assert harness.participant_data.get(key) == val, f"Key '{key}' was mutated by the node"


def test_node_does_not_add_new_participant_keys():
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(
        source,
        participant_data={
            "language_preference": "en",
            "gestational_age_at_enrollment": 29,
            "enrolled_at": _ENROLLED_AT,
        },
        now=_NOW,
    )
    before_keys = set(harness.participant_data.keys())
    harness.run("test")
    after_keys = set(harness.participant_data.keys())
    assert after_keys == before_keys, f"Node added participant keys: {after_keys - before_keys}"


# ---------------------------------------------------------------------------
# repair-1: participant key — node must read language_preference, not language
# ---------------------------------------------------------------------------

# Frozen clock matches registration test suite (10 days after enrolled).
_NOW = datetime.datetime(2026, 10, 3, 9, 30, tzinfo=datetime.UTC)
_ENROLLED_AT = "2026-09-23T09:30:00+00:00"  # 10 days before _NOW → 1 week elapsed


def test_node_uses_language_preference_key_selects_sw():
    # Node must read participant['language_preference'], not participant['language'].
    # Passing language_preference='sw' must select SW entries.
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language_preference": "sw"})
    harness.run("test")
    assert "synth_sw_a" in harness.temp_state["kb_ids"], (
        "Node must read 'language_preference'; 'sw' preference must select SW entries"
    )


def test_node_wrong_language_key_produces_no_match():
    # Passing only the old 'language' key (not 'language_preference') must not select
    # any entries — the node must not fall back to the wrong key.
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language": "sw"})
    harness.run("test")
    assert harness.temp_state["kb_available"] is False, (
        "Node must read 'language_preference'; the old 'language' key must have no effect"
    )


def test_node_absent_language_preference_produces_no_match():
    # No language_preference in participant data → no silent default to 'en'.
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={})
    harness.run("test")
    assert harness.temp_state["kb_available"] is False, (
        "Absent language_preference must not silently default to 'en'; no entries must match"
    )


# ---------------------------------------------------------------------------
# repair-1: week computation — from enrollment data, not 'current_week' key
# ---------------------------------------------------------------------------


def test_node_computes_week_from_enrollment_data():
    # gestational_age_at_enrollment=28, enrolled 10 days ago → 1 week elapsed → week 29.
    # synth_week min_week=28, max_week=40 → 29 is in range → included.
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(
        source,
        participant_data={
            "language_preference": "en",
            "gestational_age_at_enrollment": 28,
            "enrolled_at": _ENROLLED_AT,
        },
        now=_NOW,
    )
    harness.run("test")
    assert "synth_week" in harness.temp_state["kb_ids"], (
        "Node must compute current week from gestational_age_at_enrollment + enrolled_at"
    )


def test_node_excludes_ranged_entries_when_week_unknown():
    # No enrollment data → week unknown → ranged entries (min_week/max_week set) excluded.
    # General entries (no week bounds) remain eligible.
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "synth_week" not in harness.temp_state["kb_ids"], (
        "Unknown week must EXCLUDE ranged entries; current node wrongly includes them when current_week is absent"
    )
    # General entries (no week bound) must still be eligible
    assert "synth_en_a" in harness.temp_state["kb_ids"]


def test_node_excludes_week_entry_before_min_using_enrollment():
    # week = 23 + 1 = 24 → below synth_week min_week=28 → excluded.
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(
        source,
        participant_data={
            "language_preference": "en",
            "gestational_age_at_enrollment": 23,
            "enrolled_at": _ENROLLED_AT,
        },
        now=_NOW,
    )
    harness.run("test")
    assert "synth_week" not in harness.temp_state["kb_ids"]


def test_node_excludes_week_entry_after_max_using_enrollment():
    # week = 40 + 1 = 41 → above synth_week max_week=40 → excluded.
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(
        source,
        participant_data={
            "language_preference": "en",
            "gestational_age_at_enrollment": 40,
            "enrolled_at": _ENROLLED_AT,
        },
        now=_NOW,
    )
    harness.run("test")
    assert "synth_week" not in harness.temp_state["kb_ids"]


def test_node_includes_entry_at_exact_min_boundary_enrollment():
    # week = 27 + 1 = 28 → exactly at min_week=28 → included.
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(
        source,
        participant_data={
            "language_preference": "en",
            "gestational_age_at_enrollment": 27,
            "enrolled_at": _ENROLLED_AT,
        },
        now=_NOW,
    )
    harness.run("test")
    assert "synth_week" in harness.temp_state["kb_ids"]


def test_node_includes_entry_at_exact_max_boundary_enrollment():
    # week = 39 + 1 = 40 → exactly at max_week=40 → included.
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(
        source,
        participant_data={
            "language_preference": "en",
            "gestational_age_at_enrollment": 39,
            "enrolled_at": _ENROLLED_AT,
        },
        now=_NOW,
    )
    harness.run("test")
    assert "synth_week" in harness.temp_state["kb_ids"]


def test_node_safe_on_bad_enrolled_at_string():
    # Bad ISO string → no crash; ranged entry excluded (week unknown).
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(
        source,
        participant_data={
            "language_preference": "en",
            "gestational_age_at_enrollment": 28,
            "enrolled_at": "not-a-date",
        },
        now=_NOW,
    )
    harness.run("test")
    assert harness.temp_state["kb_available"] is not None  # no exception
    assert "synth_week" not in harness.temp_state["kb_ids"]


def test_node_safe_on_naive_enrolled_at():
    # Naive datetime string (no timezone) → safe handling; ranged entry excluded.
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(
        source,
        participant_data={
            "language_preference": "en",
            "gestational_age_at_enrollment": 28,
            "enrolled_at": "2026-09-23T09:30:00",  # no timezone
        },
        now=_NOW,
    )
    harness.run("test")
    assert "synth_week" not in harness.temp_state["kb_ids"]


def test_node_safe_on_non_int_gestational_age():
    # Non-integer gestational_age_at_enrollment → no crash; ranged excluded.
    source = _source_with_fixture(SYNTHETIC_ENTRIES)
    harness = NodeHarness(
        source,
        participant_data={
            "language_preference": "en",
            "gestational_age_at_enrollment": "twenty",
            "enrolled_at": _ENROLLED_AT,
        },
        now=_NOW,
    )
    harness.run("test")
    assert "synth_week" not in harness.temp_state["kb_ids"]


# ---------------------------------------------------------------------------
# repair-1: exact UTF-8 byte accounting with separator bytes in node
# ---------------------------------------------------------------------------

# Entry whose byte count differs from char count (em-dash U+2014 = 3 bytes, 1 char).
# text = 'A' * 97 + '\u2014' → 97 + 3 = 100 UTF-8 bytes, 98 chars.
_UNICODE_EN = {
    "id": "synth_unicode_en",
    "review_status": "approved",
    "language": "en",
    "text": "A" * 97 + "\u2014",  # 100 UTF-8 bytes, 98 chars
    "source_refs": ["https://example.com"],
    "topics": [],
    "min_week": None,
    "max_week": None,
}

_SHORT_EN_1 = {
    "id": "short_en_1",
    "review_status": "approved",
    "language": "en",
    "text": "A" * 100,  # 100 ASCII bytes
    "source_refs": [],
    "topics": [],
    "min_week": None,
    "max_week": None,
}
_SHORT_EN_2 = {
    "id": "short_en_2",
    "review_status": "approved",
    "language": "en",
    "text": "B",  # 1 byte
    "source_refs": [],
    "topics": [],
    "min_week": None,
    "max_week": None,
}


def test_node_unicode_text_uses_utf8_bytes_in_budget():
    # Unicode entry: 100 UTF-8 bytes, 98 chars.
    # Budget=99: must be EXCLUDED when byte-counting correctly.
    # Bug: char count (98) would include it at budget 99.
    # Inject as only entry with budget=99 by patching max_context_chars in source.
    source = _source_with_fixture([_UNICODE_EN])
    patched = source.replace("max_context_bytes = 2000", "max_context_bytes = 99", 1)
    assert patched != source, "max_context_bytes constant not found in node source"
    harness = NodeHarness(patched, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "synth_unicode_en" not in harness.temp_state["kb_ids"], (
        "Node must use UTF-8 byte count; em-dash (3 bytes) must count 3 bytes not 1 char"
    )


def test_node_separator_bytes_counted_in_budget():
    # Entry 1 = 100 bytes, Entry 2 = 1 byte, separator = 2 bytes.
    # Budget=102: 100 + 2(sep) + 1 = 103 > 102 → entry 2 must be excluded.
    # Bug: char count without separator gives 100+1=101 ≤ 102 → entry 2 included.
    source = _source_with_fixture([_SHORT_EN_1, _SHORT_EN_2])
    patched = source.replace("max_context_bytes = 2000", "max_context_bytes = 102", 1)
    assert patched != source, "max_context_bytes constant not found in node source"
    harness = NodeHarness(patched, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "short_en_1" in harness.temp_state["kb_ids"]
    assert "short_en_2" not in harness.temp_state["kb_ids"], (
        "Separator bytes (\\n\\n = 2 bytes) must be counted in the node budget"
    )


# ---------------------------------------------------------------------------
# repair-1: staging eligible flag — pending entry with eligible=True selected
# ---------------------------------------------------------------------------

_STAGED_PENDING = {
    "id": "synth_staged",
    "review_status": "pending",
    "eligible": True,  # explicit staging flag; review_status stays 'pending'
    "language": "en",
    "text": "Staged pending text for synthetic staging tests only.",
    "source_refs": [],
    "topics": [],
    "min_week": None,
    "max_week": None,
}


def test_node_staged_eligible_flag_selects_pending_entry():
    # A pending entry with eligible=True must be included (staging mode).
    # Without the eligibility flag check, the node only checks review_status=='approved'
    # and would exclude this entry.
    source = _source_with_fixture([_STAGED_PENDING])
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "synth_staged" in harness.temp_state["kb_ids"], (
        "Node must check entry.get('eligible') is True as an explicit staging eligibility flag"
    )
    assert harness.temp_state["kb_available"] is True


# ---------------------------------------------------------------------------
# repair-2: render_kb_node NodeHarness integration — must be executable source
# ---------------------------------------------------------------------------

from ocs.knowledge import render_kb_node  # noqa: E402

# Synthetic entries for integration tests — approved, language-specific, week-ranged.
_RKN_EN_A = {
    "id": "rkn_en_a",
    "review_status": "approved",
    "language": "en",
    "text": "Approved English entry A for render_kb_node integration.",
    "source_refs": ["https://example.com"],
    "topics": [],
    "min_week": None,
    "max_week": None,
}
_RKN_EN_B = {
    "id": "rkn_en_b",
    "review_status": "approved",
    "language": "en",
    "text": "Approved English entry B — slightly longer to test budget.",
    "source_refs": ["https://example.com"],
    "topics": [],
    "min_week": None,
    "max_week": None,
}
_RKN_SW_A = {
    "id": "rkn_sw_a",
    "review_status": "approved",
    "language": "sw",
    "text": "Ingizo la Kiswahili iliyoidhinishwa.",
    "source_refs": ["https://example.com"],
    "topics": [],
    "min_week": None,
    "max_week": None,
}
_RKN_WEEK = {
    "id": "rkn_week",
    "review_status": "approved",
    "language": "en",
    "text": "Week-ranged approved entry.",
    "source_refs": [],
    "topics": [],
    "min_week": 28,
    "max_week": 40,
}
_RKN_PENDING = {
    "id": "rkn_pending",
    "review_status": "pending",
    "language": "en",
    "text": "Pending entry for staging test.",
    "source_refs": [],
    "topics": [],
    "min_week": None,
    "max_week": None,
}

_RKN_ALL = [_RKN_EN_A, _RKN_EN_B, _RKN_SW_A, _RKN_WEEK, _RKN_PENDING]


def test_render_kb_node_harness_default_empty_pending_excluded():
    # With all-pending list, default render_kb_node must produce empty KB.
    source = render_kb_node([_RKN_PENDING])
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert harness.temp_state["kb_available"] is False
    assert harness.temp_state["kb_ids"] == []


def test_render_kb_node_harness_en_participant_selects_en_entries():
    source = render_kb_node(_RKN_ALL)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "rkn_en_a" in harness.temp_state["kb_ids"]
    assert "rkn_en_b" in harness.temp_state["kb_ids"]
    assert harness.temp_state["kb_available"] is True


def test_render_kb_node_harness_en_excludes_sw_entries():
    source = render_kb_node(_RKN_ALL)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "rkn_sw_a" not in harness.temp_state["kb_ids"]


def test_render_kb_node_harness_sw_participant_selects_sw_entries():
    source = render_kb_node(_RKN_ALL)
    harness = NodeHarness(source, participant_data={"language_preference": "sw"})
    harness.run("test")
    assert "rkn_sw_a" in harness.temp_state["kb_ids"]
    assert "rkn_en_a" not in harness.temp_state["kb_ids"]


def test_render_kb_node_harness_default_pending_excluded():
    # Pending entry must not be selected even when injected via default render.
    source = render_kb_node(_RKN_ALL)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "rkn_pending" not in harness.temp_state["kb_ids"]


def test_render_kb_node_harness_staging_pending_included():
    # With include_pending=True, pending entry with eligible flag is selected.
    source = render_kb_node([_RKN_PENDING], include_pending=True)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "rkn_pending" in harness.temp_state["kb_ids"]
    assert harness.temp_state["kb_available"] is True


def test_render_kb_node_harness_week_in_range_included():
    # ga=28, enrolled 10 days ago (1 week) → week 29 → in range 28-40.
    source = render_kb_node(_RKN_ALL)
    harness = NodeHarness(
        source,
        participant_data={
            "language_preference": "en",
            "gestational_age_at_enrollment": 28,
            "enrolled_at": _ENROLLED_AT,
        },
        now=_NOW,
    )
    harness.run("test")
    assert "rkn_week" in harness.temp_state["kb_ids"]


def test_render_kb_node_harness_week_out_of_range_excluded():
    # ga=41, enrolled 10 days ago (1 week) → week 42 → above max 40.
    source = render_kb_node(_RKN_ALL)
    harness = NodeHarness(
        source,
        participant_data={
            "language_preference": "en",
            "gestational_age_at_enrollment": 41,
            "enrolled_at": _ENROLLED_AT,
        },
        now=_NOW,
    )
    harness.run("test")
    assert "rkn_week" not in harness.temp_state["kb_ids"]
    # General (unbounded) EN entries are still selected
    assert "rkn_en_a" in harness.temp_state["kb_ids"]


def test_render_kb_node_harness_budget_constrains_output():
    # Very small budget: only fits rkn_en_a (60 bytes approx).
    # EN entry A text: "Approved English entry A for render_kb_node integration."
    # = 57 bytes. Set budget to 60 to include A but exclude B + separator.
    source = render_kb_node([_RKN_EN_A, _RKN_EN_B], max_context_bytes=60)
    harness = NodeHarness(source, participant_data={"language_preference": "en"})
    harness.run("test")
    assert "rkn_en_a" in harness.temp_state["kb_ids"]
    assert "rkn_en_b" not in harness.temp_state["kb_ids"]


def test_render_kb_node_harness_absent_language_produces_no_match():
    source = render_kb_node(_RKN_ALL)
    harness = NodeHarness(source, participant_data={})
    harness.run("test")
    assert harness.temp_state["kb_available"] is False
