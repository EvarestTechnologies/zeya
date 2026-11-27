"""Tests for ocs/knowledge.py: load_knowledge and render_kb_context.

Synthetic fixtures are used for all 'approved' path tests; real draft entries
must remain pending and are verified to stay that way here.
"""

from pathlib import Path

import pytest

from ocs.knowledge import load_knowledge, render_kb_context, render_kb_node

# ---------------------------------------------------------------------------
# Synthetic Markdown fixtures — approved entries for testing selection logic.
# Real knowledge-base entries are all pending; never label them approved here.
# ---------------------------------------------------------------------------

SYNTHETIC_APPROVED_MD = """\
# Test knowledge base

---

## synth_alpha

Review-state: approved
Language: en
Topics: test, education
Min-week:
Max-week:
Source-refs: https://example.com/ref1

Alpha approved text for general education.

---

## synth_beta

Review-state: approved
Language: en
Topics: test
Min-week: 20
Max-week: 36
Source-refs: https://example.com/ref2

Beta approved text valid between weeks 20 and 36.

---

## synth_pending

Review-state: pending
Language: en
Topics: test
Min-week:
Max-week:
Source-refs: https://example.com/ref3

Pending text that must be excluded by default.

---

## synth_sw

Review-state: approved
Language: sw
Topics: test
Min-week:
Max-week:
Source-refs: https://example.com/ref4

Maandishi ya lugha ya Kiswahili yaliyoidhinishwa.
"""

MALFORMED_STATUS_MD = """\
# Test knowledge base

---

## synth_no_status

Review-state:
Language: en
Topics: test
Min-week:
Max-week:
Source-refs: https://example.com/ref5

This entry has no review state and must be treated as pending.

---

## synth_bad_status

Review-state: unclear
Language: en
Topics: test
Min-week:
Max-week:
Source-refs:

This entry has an unrecognised status and must be treated as pending.
"""


@pytest.fixture
def approved_md(tmp_path):
    p = tmp_path / "kb.md"
    p.write_text(SYNTHETIC_APPROVED_MD, encoding="utf-8")
    return p


@pytest.fixture
def malformed_md(tmp_path):
    p = tmp_path / "kb_bad.md"
    p.write_text(MALFORMED_STATUS_MD, encoding="utf-8")
    return p


@pytest.fixture
def real_kb_path():
    return Path(__file__).resolve().parents[2] / "docs" / "zeya-knowledge-base.md"


# ---------------------------------------------------------------------------
# load_knowledge — entry schema
# ---------------------------------------------------------------------------


def test_load_knowledge_returns_list(approved_md):
    entries = load_knowledge(approved_md, include_pending=True)
    assert isinstance(entries, list)


def test_load_knowledge_entries_have_required_keys(approved_md):
    entries = load_knowledge(approved_md, include_pending=True)
    required = {"id", "review_status", "language", "text", "source_refs", "topics", "min_week", "max_week"}
    for entry in entries:
        assert required <= set(entry.keys()), f"Missing keys in {entry.get('id')}"


def test_load_knowledge_review_status_values_are_bounded(approved_md):
    entries = load_knowledge(approved_md, include_pending=True)
    for entry in entries:
        assert entry["review_status"] in ("pending", "approved"), entry["id"]


def test_load_knowledge_language_values_are_bounded(approved_md):
    entries = load_knowledge(approved_md, include_pending=True)
    for entry in entries:
        assert entry["language"] in ("en", "sw"), entry["id"]


def test_load_knowledge_topics_is_list(approved_md):
    entries = load_knowledge(approved_md, include_pending=True)
    for entry in entries:
        assert isinstance(entry["topics"], list), entry["id"]


def test_load_knowledge_source_refs_is_list(approved_md):
    entries = load_knowledge(approved_md, include_pending=True)
    for entry in entries:
        assert isinstance(entry["source_refs"], list), entry["id"]


def test_load_knowledge_week_fields_are_int_or_none(approved_md):
    entries = load_knowledge(approved_md, include_pending=True)
    for entry in entries:
        assert entry["min_week"] is None or isinstance(entry["min_week"], int), entry["id"]
        assert entry["max_week"] is None or isinstance(entry["max_week"], int), entry["id"]


def test_load_knowledge_parses_week_range_correctly(approved_md):
    entries = load_knowledge(approved_md, include_pending=True)
    beta = next(e for e in entries if e["id"] == "synth_beta")
    assert beta["min_week"] == 20
    assert beta["max_week"] == 36


def test_load_knowledge_text_is_nonempty_string(approved_md):
    entries = load_knowledge(approved_md, include_pending=True)
    for entry in entries:
        assert isinstance(entry["text"], str), entry["id"]
        assert entry["text"].strip(), f"Empty text in {entry['id']}"


def test_load_knowledge_entry_ids_are_strings(approved_md):
    entries = load_knowledge(approved_md, include_pending=True)
    for entry in entries:
        assert isinstance(entry["id"], str) and entry["id"], "Entry id must be a non-empty string"


# ---------------------------------------------------------------------------
# load_knowledge — approval filtering (fail-closed by default)
# ---------------------------------------------------------------------------


def test_load_knowledge_excludes_pending_by_default(approved_md):
    entries = load_knowledge(approved_md)
    assert all(e["review_status"] == "approved" for e in entries)


def test_load_knowledge_excludes_pending_when_explicit_false(approved_md):
    entries = load_knowledge(approved_md, include_pending=False)
    assert all(e["review_status"] == "approved" for e in entries)


def test_load_knowledge_includes_pending_when_requested(approved_md):
    entries = load_knowledge(approved_md, include_pending=True)
    assert any(e["review_status"] == "pending" for e in entries)


def test_load_knowledge_approved_count(approved_md):
    # synth_alpha, synth_beta, synth_sw are approved; synth_pending is not
    entries = load_knowledge(approved_md)
    assert len(entries) == 3


def test_load_knowledge_total_count_with_pending(approved_md):
    entries = load_knowledge(approved_md, include_pending=True)
    assert len(entries) == 4


# ---------------------------------------------------------------------------
# load_knowledge — malformed review-state fails closed
# ---------------------------------------------------------------------------


def test_malformed_review_status_excluded_by_default(malformed_md):
    entries = load_knowledge(malformed_md)
    assert len(entries) == 0, "Entries with missing/unknown review status must not be treated as approved"


def test_malformed_review_status_treated_as_pending(malformed_md):
    entries = load_knowledge(malformed_md, include_pending=True)
    for entry in entries:
        assert entry["review_status"] == "pending", f"{entry['id']} should be pending"


# ---------------------------------------------------------------------------
# Real knowledge-base: all five entries must remain pending
# ---------------------------------------------------------------------------


def test_real_kb_all_entries_are_pending(real_kb_path):
    entries = load_knowledge(real_kb_path, include_pending=True)
    assert len(entries) == 10, f"Expected 10 entries (5 en + 5 sw), got {len(entries)}"
    for entry in entries:
        assert entry["review_status"] == "pending", (
            f"Entry '{entry['id']}' (lang={entry['language']}) must remain pending — "
            "no clinical or language approval has been given for the v0.1 draft"
        )


def test_real_kb_excludes_all_entries_by_default(real_kb_path):
    entries = load_knowledge(real_kb_path)
    assert len(entries) == 0, "No real KB entries must be approved; all must remain pending"


def test_real_kb_expected_ids(real_kb_path):
    entries = load_knowledge(real_kb_path, include_pending=True)
    ids = {e["id"] for e in entries}
    expected = {"anc_purpose", "pregnancy_records", "food_variety", "food_safety", "birth_preparation"}
    assert ids == expected


def test_real_kb_english_entries_remain_english(real_kb_path):
    """The five English KB entries must remain language='en', pending, and unchanged."""
    entries = load_knowledge(real_kb_path, include_pending=True)
    en_entries = [e for e in entries if e["language"] == "en"]
    assert len(en_entries) == 5, (
        f"Expected exactly 5 en KB entries; got {len(en_entries)}. "
        "No new English entries should be added in this branch."
    )
    for entry in en_entries:
        assert entry["language"] == "en", f"Entry '{entry['id']}' classified as en but language={entry['language']!r}"
        assert entry["review_status"] == "pending"


def test_real_kb_sw_entries_are_sw_and_pending(real_kb_path):
    """The five Kiswahili draft KB entries must have language='sw' and remain pending.

    Kiswahili translations require a separate fluent-speaker and clinical review
    before any entry can be approved.  All five sw entries must remain pending.
    """
    entries = load_knowledge(real_kb_path, include_pending=True)
    sw_entries = [e for e in entries if e["language"] == "sw"]
    assert len(sw_entries) == 5, f"Expected exactly 5 sw KB entries (pending draft), got {len(sw_entries)}."
    for entry in sw_entries:
        assert entry["language"] == "sw", f"Entry '{entry['id']}' classified as sw but language={entry['language']!r}"
        assert entry["review_status"] == "pending", (
            f"sw entry '{entry['id']}' must remain pending — "
            "Kiswahili translation requires separate fluent-speaker and clinical review."
        )


def test_real_kb_entries_have_source_refs(real_kb_path):
    entries = load_knowledge(real_kb_path, include_pending=True)
    for entry in entries:
        assert entry["source_refs"], f"Entry '{entry['id']}' has no source references"


# ---------------------------------------------------------------------------
# render_kb_context — in-memory approved entry fixtures
# ---------------------------------------------------------------------------

APPROVED_ENTRIES = [
    {
        "id": "alpha",
        "review_status": "approved",
        "language": "en",
        "text": "Alpha text.",
        "source_refs": ["https://example.com/1"],
        "topics": ["test"],
        "min_week": None,
        "max_week": None,
    },
    {
        "id": "beta",
        "review_status": "approved",
        "language": "en",
        "text": "Beta text.",
        "source_refs": ["https://example.com/2"],
        "topics": ["test"],
        "min_week": None,
        "max_week": None,
    },
]


def test_render_returns_tuple_of_text_and_ids():
    result = render_kb_context(APPROVED_ENTRIES)
    assert isinstance(result, tuple) and len(result) == 2


def test_render_empty_entries_returns_empty_text_and_ids():
    text, ids = render_kb_context([])
    assert text == ""
    assert ids == []


def test_render_single_entry_returns_its_text():
    text, ids = render_kb_context(APPROVED_ENTRIES[:1])
    assert "Alpha text." in text
    assert ids == ["alpha"]


def test_render_multiple_entries_includes_all_within_budget():
    text, ids = render_kb_context(APPROVED_ENTRIES)
    assert "Alpha text." in text
    assert "Beta text." in text
    assert set(ids) == {"alpha", "beta"}


def test_render_respects_byte_budget_stops_at_first_overflow():
    # Each entry is 100 ASCII bytes; budget 110 → first fits, second overflows
    small_entries = [
        {
            "id": "first",
            "review_status": "approved",
            "language": "en",
            "text": "A" * 100,
            "source_refs": [],
            "topics": [],
            "min_week": None,
            "max_week": None,
        },
        {
            "id": "second",
            "review_status": "approved",
            "language": "en",
            "text": "B" * 100,
            "source_refs": [],
            "topics": [],
            "min_week": None,
            "max_week": None,
        },
    ]
    text, ids = render_kb_context(small_entries, max_context_bytes=110)
    assert "first" in ids
    assert "second" not in ids


def test_render_ids_match_included_entries():
    text, ids = render_kb_context(APPROVED_ENTRIES)
    assert ids == ["alpha", "beta"]


# ---------------------------------------------------------------------------
# repair-1: render_kb_context — separator bytes must be included in budget
# ---------------------------------------------------------------------------

_SEP_ENTRY_A = {
    "id": "sep_a",
    "review_status": "approved",
    "language": "en",
    "text": "A" * 100,  # 100 ASCII bytes
    "source_refs": [],
    "topics": [],
    "min_week": None,
    "max_week": None,
}
_SEP_ENTRY_B = {
    "id": "sep_b",
    "review_status": "approved",
    "language": "en",
    "text": "B",  # 1 ASCII byte
    "source_refs": [],
    "topics": [],
    "min_week": None,
    "max_week": None,
}


def test_render_kb_context_separator_bytes_included_in_budget():
    # A=100 bytes, B=1 byte, separator=2 bytes ('\n\n').
    # Budget=102: A fits (100), then A+sep+B = 103 > 102 → B must be excluded.
    # Bug: without separator bytes counted, 100+1=101 ≤ 102 would include B.
    text, ids = render_kb_context([_SEP_ENTRY_A, _SEP_ENTRY_B], max_context_bytes=102)
    assert "sep_a" in ids
    assert "sep_b" not in ids, (
        "Separator bytes (\\n\\n = 2 bytes) must be counted toward the budget; sep_b was wrongly included"
    )


def test_render_kb_context_separator_bytes_allow_first_entry_alone():
    # Even at budget=100 (exact size of A), A alone must still be included.
    text, ids = render_kb_context([_SEP_ENTRY_A, _SEP_ENTRY_B], max_context_bytes=100)
    assert "sep_a" in ids
    assert "sep_b" not in ids


def test_render_kb_context_unicode_uses_utf8_byte_count():
    # Em-dash '\u2014' is 3 bytes in UTF-8, 1 char.
    # text = 'A' * 97 + '\u2014' = 97 + 3 = 100 UTF-8 bytes; char count = 98.
    unicode_entry = {
        "id": "uni",
        "review_status": "approved",
        "language": "en",
        "text": "A" * 97 + "\u2014",  # 100 UTF-8 bytes
        "source_refs": [],
        "topics": [],
        "min_week": None,
        "max_week": None,
    }
    # Budget=99: entry is 100 bytes → must be excluded (UTF-8 counted).
    # Bug: char count (98) would include it.
    text, ids = render_kb_context([unicode_entry], max_context_bytes=99)
    assert "uni" not in ids, (
        "render_kb_context must use exact UTF-8 byte count; Unicode multi-byte chars must count their full byte width"
    )


# ---------------------------------------------------------------------------
# repair-1: load_knowledge validation — approved entries must pass integrity checks
# ---------------------------------------------------------------------------


def _write_md(tmp_path, content, name="kb.md"):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_load_knowledge_raises_on_duplicate_id_language(tmp_path):
    md = _write_md(
        tmp_path,
        """\
# Test

---

## dup_entry

Review-state: approved
Language: en
Topics: test
Min-week:
Max-week:
Source-refs: https://example.com/ref1

First body for dup_entry in English.

---

## dup_entry

Review-state: approved
Language: en
Topics: test
Min-week:
Max-week:
Source-refs: https://example.com/ref2

Second body for dup_entry in English — must be rejected.
""",
    )
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        load_knowledge(md, include_pending=True)


def test_load_knowledge_raises_on_empty_body_approved(tmp_path):
    md = _write_md(
        tmp_path,
        """\
# Test

---

## empty_body

Review-state: approved
Language: en
Topics: test
Min-week:
Max-week:
Source-refs: https://example.com/ref1

""",
    )
    with pytest.raises(ValueError, match="[Ee]mpty|[Bb]ody|[Tt]ext"):
        load_knowledge(md)


def test_load_knowledge_raises_on_empty_source_refs_approved(tmp_path):
    md = _write_md(
        tmp_path,
        """\
# Test

---

## no_refs

Review-state: approved
Language: en
Topics: test
Min-week:
Max-week:
Source-refs:

Body text present but no source reference.
""",
    )
    with pytest.raises(ValueError, match="[Ss]ource"):
        load_knowledge(md)


def test_load_knowledge_raises_on_inverted_week_bounds_approved(tmp_path):
    md = _write_md(
        tmp_path,
        """\
# Test

---

## inverted_bounds

Review-state: approved
Language: en
Topics: test
Min-week: 30
Max-week: 20
Source-refs: https://example.com/ref1

Body text with min_week > max_week.
""",
    )
    with pytest.raises(ValueError, match="[Bb]ound|[Ww]eek"):
        load_knowledge(md)


def test_load_knowledge_raises_on_unsupported_language_for_approved(tmp_path):
    md = _write_md(
        tmp_path,
        """\
# Test

---

## fr_entry

Review-state: approved
Language: fr
Topics: test
Min-week:
Max-week:
Source-refs: https://example.com/ref1

Corps du texte en français.
""",
    )
    with pytest.raises(ValueError, match="[Ll]anguage"):
        load_knowledge(md)


def test_load_knowledge_unsupported_language_pending_not_normalized(tmp_path):
    # Pending entry with unsupported language must NOT be silently relabelled 'en'.
    md = _write_md(
        tmp_path,
        """\
# Test

---

## fr_pending

Review-state: pending
Language: fr
Topics: test
Min-week:
Max-week:
Source-refs:

Contenu en français, en attente de révision.
""",
    )
    entries = load_knowledge(md, include_pending=True)
    fr_entry = next((e for e in entries if e["id"] == "fr_pending"), None)
    assert fr_entry is not None
    assert fr_entry["language"] == "fr", (
        f"Unsupported language must NOT be silently relabelled to 'en'; got {fr_entry['language']!r}"
    )


def test_load_knowledge_pending_duplicate_id_language_raises(tmp_path):
    # Duplicate (id, language) is invalid even for pending entries.
    md = _write_md(
        tmp_path,
        """\
# Test

---

## dup_pend

Review-state: pending
Language: en
Topics: test
Min-week:
Max-week:
Source-refs:

First pending entry with this id.

---

## dup_pend

Review-state: pending
Language: en
Topics: test
Min-week:
Max-week:
Source-refs:

Second pending entry with same id — must be rejected.
""",
    )
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        load_knowledge(md, include_pending=True)


# ---------------------------------------------------------------------------
# repair-2: render_kb_node — must return executable str, not a tuple
# ---------------------------------------------------------------------------


def test_render_kb_node_returns_str():
    assert isinstance(render_kb_node([]), str), "render_kb_node must return executable Python str"


def test_render_kb_node_is_non_empty_str():
    assert len(render_kb_node([])) > 0


def test_render_kb_node_contains_main_function():
    assert "def main(" in render_kb_node([])


def test_render_kb_node_placeholder_replaced():
    # The original empty-list placeholder must not survive in the output.
    source = render_kb_node([])
    assert 'KB_JSON = "[]"' not in source, "KB_JSON placeholder must be replaced by injection"


def test_render_kb_node_validates_bool_budget():
    with pytest.raises(ValueError, match="[Ii]nt|[Bb]ool|bool"):
        render_kb_node([], max_context_bytes=True)


def test_render_kb_node_validates_false_budget():
    with pytest.raises(ValueError, match="[Ii]nt|[Bb]ool|bool"):
        render_kb_node([], max_context_bytes=False)


def test_render_kb_node_validates_negative_budget():
    with pytest.raises(ValueError, match="[Pp]ositive"):
        render_kb_node([], max_context_bytes=-1)


def test_render_kb_node_validates_zero_budget():
    with pytest.raises(ValueError, match="[Pp]ositive"):
        render_kb_node([], max_context_bytes=0)


def test_render_kb_node_accepts_valid_int_budget():
    source = render_kb_node([], max_context_bytes=500)
    assert isinstance(source, str)


def test_render_kb_node_pending_excluded_by_default():
    # Pending entry must NOT appear in the injected KB_JSON (default pending excluded).
    entries = [
        {
            "id": "pend_check",
            "review_status": "pending",
            "language": "en",
            "text": "Pending text that must be absent.",
            "source_refs": [],
            "topics": [],
            "min_week": None,
            "max_week": None,
        },
    ]
    source = render_kb_node(entries)
    assert "pend_check" not in source


def test_render_kb_node_approved_included_in_source():
    entries = [
        {
            "id": "appr_check",
            "review_status": "approved",
            "language": "en",
            "text": "Approved text that must be present.",
            "source_refs": ["https://example.com"],
            "topics": [],
            "min_week": None,
            "max_week": None,
        },
    ]
    source = render_kb_node(entries)
    assert "appr_check" in source


def test_render_kb_node_staging_pending_in_source():
    # With include_pending=True, pending entry must appear in source JSON.
    entries = [
        {
            "id": "staged_check",
            "review_status": "pending",
            "language": "en",
            "text": "Staged pending text.",
            "source_refs": [],
            "topics": [],
            "min_week": None,
            "max_week": None,
        },
    ]
    source = render_kb_node(entries, include_pending=True)
    assert "staged_check" in source


def test_render_kb_node_does_not_change_review_status_in_staging():
    # Staging mode must add 'eligible' flag but NEVER change review_status to 'approved'.
    entries = [
        {
            "id": "staged",
            "review_status": "pending",
            "language": "en",
            "text": "Staged pending entry.",
            "source_refs": [],
            "topics": [],
            "min_week": None,
            "max_week": None,
        },
    ]
    _ = render_kb_node(entries, include_pending=True)
    assert entries[0]["review_status"] == "pending", "render_kb_node must never relabel a pending entry as approved"


# ---------------------------------------------------------------------------
# repair-2: week metadata validation — malformed bounds must fail for approved
# ---------------------------------------------------------------------------


def _md_with_week(tmp_path, min_week_val, max_week_val, name="wb.md"):
    """Write a minimal approved entry with the given raw week field values."""
    content = f"""\
# Test

---

## week_check

Review-state: approved
Language: en
Topics: test
Min-week: {min_week_val}
Max-week: {max_week_val}
Source-refs: https://example.com/ref1

Body text for week validation test.
"""
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_load_knowledge_raises_on_text_min_week_approved(tmp_path):
    # "thirty" is not a valid positive integer week.
    with pytest.raises(ValueError, match="[Ww]eek|[Mm]alformed|[Ii]nvalid"):
        load_knowledge(_md_with_week(tmp_path, "thirty", ""))


def test_load_knowledge_raises_on_negative_min_week_approved(tmp_path):
    # "-5" is not a valid week (not a digit string).
    with pytest.raises(ValueError, match="[Ww]eek|[Mm]alformed|[Ii]nvalid"):
        load_knowledge(_md_with_week(tmp_path, "-5", ""))


def test_load_knowledge_raises_on_decimal_min_week_approved(tmp_path):
    # "30.5" is not a valid integer week.
    with pytest.raises(ValueError, match="[Ww]eek|[Mm]alformed|[Ii]nvalid"):
        load_knowledge(_md_with_week(tmp_path, "30.5", ""))


def test_load_knowledge_raises_on_zero_min_week_approved(tmp_path):
    # "0" is not a valid gestational week (must be >= 1).
    with pytest.raises(ValueError, match="[Ww]eek|[Mm]alformed|[Ii]nvalid|[Bb]ound"):
        load_knowledge(_md_with_week(tmp_path, "0", ""))


def test_load_knowledge_raises_on_out_of_bounds_min_week_approved(tmp_path):
    # "300" exceeds the maximum valid gestational week.
    with pytest.raises(ValueError, match="[Ww]eek|[Mm]alformed|[Ii]nvalid|[Bb]ound"):
        load_knowledge(_md_with_week(tmp_path, "300", ""))


def test_load_knowledge_raises_on_text_max_week_approved(tmp_path):
    with pytest.raises(ValueError, match="[Ww]eek|[Mm]alformed|[Ii]nvalid"):
        load_knowledge(_md_with_week(tmp_path, "", "forty"))


def test_load_knowledge_raises_on_decimal_max_week_approved(tmp_path):
    with pytest.raises(ValueError, match="[Ww]eek|[Mm]alformed|[Ii]nvalid"):
        load_knowledge(_md_with_week(tmp_path, "", "40.5"))


def test_load_knowledge_empty_week_bounds_are_valid_for_approved(tmp_path):
    # Empty min/max week = unrestricted = valid.
    entries = load_knowledge(_md_with_week(tmp_path, "", ""))
    assert len(entries) == 1
    assert entries[0]["min_week"] is None
    assert entries[0]["max_week"] is None


def test_load_knowledge_valid_week_bounds_accepted_for_approved(tmp_path):
    entries = load_knowledge(_md_with_week(tmp_path, "20", "36"))
    assert entries[0]["min_week"] == 20
    assert entries[0]["max_week"] == 36


def test_load_knowledge_malformed_week_pending_is_allowed(tmp_path):
    # Malformed week on a PENDING entry must NOT raise; pending entries
    # bypass the approved-only integrity check.
    content = """\
# Test

---

## pend_bad_week

Review-state: pending
Language: en
Topics: test
Min-week: thirty
Max-week:
Source-refs:

Pending body text.
"""
    p = tmp_path / "pend_wk.md"
    p.write_text(content, encoding="utf-8")
    entries = load_knowledge(p, include_pending=True)
    assert len(entries) == 1
    assert entries[0]["review_status"] == "pending"
