"""
Release rules from docs/work-orders/2026-11-27-guideline-alignment.md (task 10).

1. No participant-facing string or prompt names WHO (legacy backend included), or uses an event or audience
   name ("GDHF", "Bangkok", "demo", "funder").
2. Every runtime knowledge entry cites a Ministry of Health document (HB, NG24 or BOP).
3. The handbook sentence on iron and folic acid passes the output guard (sign-off B4),
   while other medicine wording stays blocked.
"""

import re
from pathlib import Path

import pytest

from ocs.knowledge import load_knowledge
from ocs.output_policy import load_output_policy, render_output_guard
from ocs.tests.sandbox import NodeHarness

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_FILES = (
    sorted((ROOT / "ocs" / "nodes").glob("*.py"))
    + sorted((ROOT / "ocs" / "prompts").glob("*"))
    + [
        ROOT / "docs" / "zeya-knowledge-base.md",
        ROOT / "docs" / "answer-cards.yaml",
    ]
)
# The legacy backend must not serve participants (#30), but its prompt and API text
# still must not name WHO.
BACKEND_FILES = sorted((ROOT / "backend" / "app").rglob("*.py"))
WHO = re.compile(r"\bWHO\b")  # case-sensitive: the word "who" is allowed
EVENT_WORDS = re.compile(r"gdhf|bangkok|demo|funder", re.IGNORECASE)
MOH_SOURCE = re.compile(r"^(HB|NG24|BOP)\b")


@pytest.mark.parametrize("path", RUNTIME_FILES + BACKEND_FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_runtime_text_does_not_name_who(path):
    hits = [line for line in path.read_text().splitlines() if WHO.search(line)]
    assert hits == [], f"{path.name} names WHO: {hits}"


@pytest.mark.parametrize("path", RUNTIME_FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_runtime_text_has_no_event_or_audience_names(path):
    hits = [line for line in path.read_text().splitlines() if EVENT_WORDS.search(line)]
    assert hits == [], f"{path.name} uses an event or audience name: {hits}"


def test_every_runtime_entry_cites_a_ministry_document():
    entries = load_knowledge(ROOT / "docs" / "zeya-knowledge-base.md", include_pending=True)
    assert entries, "the runtime knowledge base must not be empty"
    for entry in entries:
        refs = entry["source_refs"]
        assert refs, f"{entry['id']} ({entry['language']}) has no Source-refs"
        assert all(MOH_SOURCE.match(ref) for ref in refs), (
            f"{entry['id']} ({entry['language']}) cites a non-Ministry source: {refs}"
        )


def _guard(text):
    policy = load_output_policy(str(ROOT / "docs" / "output-policy.json"))
    harness = NodeHarness(
        render_output_guard(policy),
        temp_state={"answer_route": "ASK_AI"},
        participant_data={"language_preference": "en"},
    )
    harness.run(text)
    return harness.temp_state["guard_route"]


def test_handbook_iron_and_folic_acid_sentence_passes_the_guard():
    assert _guard("Take iron and folic acid supplements every day throughout pregnancy.") == "PASS"


@pytest.mark.parametrize("text", ["Take iron tablets 60 mg daily.", "Take paracetamol for the pain."])
def test_other_medicine_wording_is_still_blocked(text):
    assert _guard(text) == "guard_blocked"
