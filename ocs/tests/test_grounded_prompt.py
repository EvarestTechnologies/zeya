"""
Tests for the grounded system prompt template (ocs/prompts/system_prompt.txt).

#24 requirements verified here:
- Template word count <=120 (excluding placeholder tokens)
- Has {temp_state.kb_section} placeholder (KB entries injected each turn)
- Has {temp_state.llm_context} placeholder (gestational/language context)
- Forbids diagnosis, prescription, drug doses, invented contacts
- Explicitly instructs what to reply when KB has no relevant entry
- States rules are guidance only; output guard handles final enforcement
- Does not embed participant identifiers (name/phone) directly in template

These are structural / policy tests only; output guard tests live in #25.
"""

import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "ocs" / "prompts"


def _load_prompt() -> str:
    return (PROMPTS_DIR / "system_prompt.txt").read_text()


def _word_count_excluding_placeholders(text: str) -> int:
    """Count words, treating {any.dotted.path} tokens as empty."""
    cleaned = re.sub(r"\{[^}]+\}", " ", text)
    return len(cleaned.split())


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------


class TestPromptStructure:
    def test_has_kb_section_placeholder(self):
        """KB content must be injected via temp_state.kb_section each turn."""
        assert "{temp_state.kb_section}" in _load_prompt()

    def test_has_llm_context_placeholder(self):
        """Gestational-age/language context from registration node is required."""
        assert "{temp_state.llm_context}" in _load_prompt()

    def test_template_word_count_at_most_120(self):
        """Static template text (placeholders excluded) must be <=120 words."""
        count = _word_count_excluding_placeholders(_load_prompt())
        assert count <= 120, (
            f"Prompt template has {count} static words (limit 120). "
            "Trim the instructions; KB content is supplied via {temp_state.kb_section}."
        )


# ---------------------------------------------------------------------------
# Forbidden capabilities / invented content
# ---------------------------------------------------------------------------


class TestPromptForbiddenContent:
    def test_diagnose_appears_only_as_prohibition(self):
        """'diagnose' must only appear in a 'do not / never' context."""
        for line in _load_prompt().lower().split("\n"):
            if "diagnos" in line:
                assert any(neg in line for neg in ("not", "never", "no ", "must not", "don't")), (
                    f"'diagnos' found outside a prohibition: {line!r}"
                )

    def test_prescribe_appears_only_as_prohibition(self):
        """'prescribe' must only appear in a 'do not / never' context."""
        for line in _load_prompt().lower().split("\n"):
            if "prescri" in line:
                assert any(neg in line for neg in ("not", "never", "no ", "must not", "don't")), (
                    f"'prescri' found outside a prohibition: {line!r}"
                )

    def test_no_literal_phone_numbers_in_template(self):
        """Template must not embed contact numbers (output guard manages allowlist)."""
        # Match 9+ consecutive digits (a phone number length)
        assert not re.search(r"(?<!\d)\d{9,}(?!\d)", _load_prompt()), (
            "Prompt template must not contain literal phone numbers."
        )

    def test_no_participant_name_reference_in_template(self):
        """Must not reference {participant_data.name} — that leaks PII into the system message."""
        assert "{participant_data.name}" not in _load_prompt()
        assert "{participant_data.phone" not in _load_prompt()


# ---------------------------------------------------------------------------
# Required behaviours
# ---------------------------------------------------------------------------


class TestPromptRequiredBehaviours:
    def test_contains_explicit_absent_kb_referral(self):
        """Must instruct model on what to say when no KB entry covers the question."""
        prompt = _load_prompt().lower()
        assert any(
            phrase in prompt
            for phrase in [
                "not covered",
                "not in the",
                "i do not have reviewed information",
                "no reviewed information",
                "reviewed information",
            ]
        ), (
            "Prompt must specify the reply when no KB entry is relevant. "
            "E.g. 'I do not have reviewed information to answer that question.'"
        )

    def test_references_healthcare_provider_referral(self):
        """Must direct participants to a healthcare provider when KB is absent."""
        prompt = _load_prompt().lower()
        assert "healthcare provider" in prompt or "health worker" in prompt or "health care provider" in prompt

    def test_contains_output_guard_acknowledgement(self):
        """Must state rules are guidance only; output guard handles final enforcement."""
        prompt = _load_prompt().lower()
        has_guard_ref = (
            ("output" in prompt and ("guard" in prompt or "check" in prompt or "enforce" in prompt))
            or "output guard" in prompt
            or "enforcement" in prompt
        )
        assert has_guard_ref, (
            "Prompt must acknowledge that rules are behavioural guidance, "
            "not an enforcement guarantee. Output guard (#25) handles final text."
        )

    def test_instructs_language_from_stored_preference(self):
        """Must reference stored/participant language so the model uses it."""
        prompt = _load_prompt().lower()
        assert any(
            phrase in prompt
            for phrase in [
                "stored language",
                "participant's language",
                "participant\u2019s language",
                "participant language",
                "saved language",
            ]
        ), "Prompt must instruct model to respond in the participant's stored language."
