"""
Tests for the privacy-preserving LLM input node (ocs/nodes/llm_input.py).

#24 requirements verified here:
- Sanitizes known saved participant name from the question (whole-word, case-insensitive)
- Removes phone patterns: +254XXXXXXXXX, 0712345678, 0112345678, 254XXXXXXXXX
- Removes email patterns
- Preserves pregnancy-week numbers (e.g. "24 weeks", "week 20")
- Passes ordinary question text through unchanged
- Does NOT modify participant data
- Does NOT set registration_route or other unexpected temp state
- Handles absent/empty participant data gracefully
"""

from ocs.tests.conftest import node_source
from ocs.tests.sandbox import NodeHarness


def _source() -> str:
    return node_source("llm_input")


def _run(message: str, participant_data: dict | None = None) -> NodeHarness:
    h = NodeHarness(_source(), participant_data=participant_data)
    h.output = h.run(message)
    return h


# ---------------------------------------------------------------------------
# Passthrough — no PII present
# ---------------------------------------------------------------------------


class TestPassthrough:
    def test_ordinary_question_unchanged(self):
        h = _run(
            "What should I eat during pregnancy?",
            {"name": "Akinyi", "language_preference": "en"},
        )
        assert h.output == "What should I eat during pregnancy?"

    def test_empty_message_returns_empty(self):
        assert _run("", {"name": "Akinyi"}).output == ""

    def test_no_participant_data_returns_unchanged(self):
        assert _run("What should I eat?", {}).output == "What should I eat?"

    def test_absent_participant_data_does_not_raise(self):
        # NodeHarness passes participant_data=None to get_participant_data()
        h = _run("What should I eat?", None)
        assert h.output == "What should I eat?"

    def test_week_numbers_preserved_in_question(self):
        h = _run(
            "I am 24 weeks pregnant, what food is good?",
            {"name": "Akinyi"},
        )
        assert "24 weeks" in h.output

    def test_pregnancy_week_reference_preserved(self):
        h = _run("What happens at week 20 of pregnancy?", {"name": "Akinyi"})
        assert "week 20" in h.output

    def test_small_week_number_not_misread_as_phone(self):
        # "07 weeks" must not be treated as the start of a phone number
        h = _run("I am 07 weeks pregnant.", {})
        assert "07 weeks" in h.output

    def test_swahili_text_preserved(self):
        h = _run(
            "Nina wiki 20 za ujauzito, nini nile?",
            {"name": "Akinyi", "language_preference": "sw"},
        )
        assert "20" in h.output
        assert "wiki" in h.output


# ---------------------------------------------------------------------------
# Name sanitization
# ---------------------------------------------------------------------------


class TestNameSanitization:
    def test_name_removed_from_question(self):
        h = _run(
            "My name is Akinyi, what should I eat?",
            {"name": "Akinyi"},
        )
        assert "Akinyi" not in h.output

    def test_name_replaced_with_placeholder(self):
        h = _run(
            "My name is Akinyi, what should I eat?",
            {"name": "Akinyi"},
        )
        assert "[name]" in h.output

    def test_name_matched_case_insensitively(self):
        h = _run("AKINYI wants to know about iron.", {"name": "Akinyi"})
        assert "AKINYI" not in h.output
        assert "[name]" in h.output

    def test_no_name_key_message_unchanged(self):
        h = _run("What should I eat?", {"language_preference": "en"})
        assert h.output == "What should I eat?"

    def test_empty_name_does_not_alter_message(self):
        h = _run("What should I eat?", {"name": "", "language_preference": "en"})
        assert h.output == "What should I eat?"

    def test_name_not_removed_mid_word(self):
        """Word-boundary matching: 'Aki' should not truncate 'Akili'."""
        h = _run("Akili ni nuru.", {"name": "Aki"})
        # "Aki" as standalone token IS removed; "Akili" (different word) must survive
        assert "Akili" in h.output

    def test_standalone_name_token_removed(self):
        h = _run("Ask Aki about it.", {"name": "Aki"})
        assert "Aki" not in h.output

    def test_multiple_name_occurrences_all_removed(self):
        h = _run(
            "Akinyi is asking: what should Akinyi eat?",
            {"name": "Akinyi"},
        )
        assert "Akinyi" not in h.output
        assert h.output.count("[name]") == 2

    def test_rest_of_message_preserved_after_name_removal(self):
        h = _run(
            "My name is Akinyi. I am 20 weeks pregnant.",
            {"name": "Akinyi"},
        )
        assert "20 weeks pregnant" in h.output


# ---------------------------------------------------------------------------
# Phone sanitization
# ---------------------------------------------------------------------------


class TestPhoneSanitization:
    def test_international_prefix_phone_removed(self):
        h = _run("Call me on +254712345678.", {})
        assert "+254712345678" not in h.output
        assert "[phone]" in h.output

    def test_local_07_phone_removed(self):
        h = _run("My number is 0712345678.", {})
        assert "0712345678" not in h.output
        assert "[phone]" in h.output

    def test_01_prefix_phone_removed(self):
        h = _run("Contact: 0112345678", {})
        assert "0112345678" not in h.output
        assert "[phone]" in h.output

    def test_254_prefix_no_plus_removed(self):
        h = _run("WhatsApp me on 254712345678", {})
        assert "254712345678" not in h.output
        assert "[phone]" in h.output

    def test_message_without_phone_unchanged(self):
        h = _run("I am 24 weeks pregnant.", {"name": "X"})
        assert "[phone]" not in h.output

    def test_07_followed_by_space_not_a_phone(self):
        h = _run("I am 07 weeks pregnant.", {})
        assert "[phone]" not in h.output
        assert "07 weeks" in h.output


# ---------------------------------------------------------------------------
# Email sanitization
# ---------------------------------------------------------------------------


class TestEmailSanitization:
    def test_email_removed(self):
        h = _run("Email me at mama@example.com for more info.", {})
        assert "mama@example.com" not in h.output
        assert "[email]" in h.output

    def test_message_without_email_unchanged(self):
        h = _run("What vitamins should I take?", {})
        assert "[email]" not in h.output

    def test_rest_of_message_preserved_after_email_removal(self):
        h = _run("Contact me at mama@example.com. I am 20 weeks.", {})
        assert "20 weeks" in h.output


# ---------------------------------------------------------------------------
# Side-effect isolation
# ---------------------------------------------------------------------------


class TestSideEffects:
    def test_participant_data_not_modified(self):
        data = {
            "name": "Akinyi",
            "language_preference": "en",
            "gestational_age_at_enrollment": 20,
        }
        h = _run("My name is Akinyi.", dict(data))
        assert h.participant_data == data

    def test_no_registration_route_set(self):
        h = _run("What should I eat?", {"name": "Akinyi"})
        assert "registration_route" not in h.temp_state

    def test_no_unexpected_temp_state_written(self):
        h = _run("What should I eat?", {"name": "Akinyi"})
        # Only user_input is preset by NodeHarness; node must not add other keys
        allowed = {"user_input"}
        unexpected = set(h.temp_state.keys()) - allowed
        assert not unexpected, f"Node wrote unexpected temp_state keys: {unexpected}"

    def test_combined_pii_all_sanitized(self):
        """Name, phone and email in one message all stripped."""
        h = _run(
            "Hi I am Akinyi, call 0712345678 or mail me at a@b.com.",
            {"name": "Akinyi"},
        )
        assert "Akinyi" not in h.output
        assert "0712345678" not in h.output
        assert "a@b.com" not in h.output


# ---------------------------------------------------------------------------
# Separated phone forms — spaced and hyphenated variants
# acceptance-findings-1.md §24: "+254 712 345 678, 0712-345-678 and
# international formats leak through"
# ---------------------------------------------------------------------------


class TestPhoneSeparatedForms:
    """Exact before/after tests for each separator style."""

    def test_spaced_international_removed(self):
        # +254 712 345 678 — space-separated international Kenya number
        h = _run("Call me on +254 712 345 678 please.", {})
        assert "[phone]" in h.output
        assert "+254 712 345 678" not in h.output

    def test_hyphenated_local_removed(self):
        # 0712-345-678 — hyphen-separated local Kenya number
        h = _run("My number is 0712-345-678.", {})
        assert "[phone]" in h.output
        assert "0712-345-678" not in h.output

    def test_hyphenated_international_removed(self):
        # +254-712-345-678 — hyphen-separated international
        h = _run("Contact: +254-712-345-678", {})
        assert "[phone]" in h.output
        assert "+254-712-345-678" not in h.output

    def test_spaced_local_removed(self):
        # 0712 345 678 — space-separated local
        h = _run("Ring 0712 345 678 today.", {})
        assert "[phone]" in h.output
        assert "0712 345 678" not in h.output

    def test_mixed_separators_removed(self):
        # +254 712-345 678 — mixed space and hyphen
        h = _run("WhatsApp +254 712-345 678", {})
        assert "[phone]" in h.output
        assert "+254 712-345 678" not in h.output

    def test_01_prefix_spaced_removed(self):
        # 0112-345-678 — 01-prefix with hyphens
        h = _run("Dial 0112-345-678.", {})
        assert "[phone]" in h.output
        assert "0112-345-678" not in h.output

    def test_254_no_plus_spaced_removed(self):
        # 254 712 345 678 — no leading +
        h = _run("Send to 254 712 345 678", {})
        assert "[phone]" in h.output
        assert "254 712 345 678" not in h.output

    # --- Preservation controls: exact captured inputs that must NOT match ---

    def test_date_07_08_not_a_phone(self):
        # Slash separator is not a valid phone separator; must be preserved exactly
        h = _run("My due date is 07/08/2025.", {})
        assert "[phone]" not in h.output
        assert "07/08/2025" in h.output

    def test_week_07_in_sentence_not_a_phone(self):
        # "week 07" — digit followed by a non-digit word
        h = _run("I am at week 07 of my pregnancy.", {})
        assert "[phone]" not in h.output
        assert "07" in h.output

    def test_number_too_short_not_treated_as_phone(self):
        # 07 1234 — only 6 digits total, below 9-digit threshold
        h = _run("Code is 07 1234.", {})
        assert "[phone]" not in h.output

    def test_message_text_after_separated_phone_preserved(self):
        # Rest of message survives phone removal
        h = _run("Call 0712-345-678 for antenatal clinic at week 20.", {})
        assert "[phone]" in h.output
        assert "week 20" in h.output
        assert "antenatal clinic" in h.output


# ---------------------------------------------------------------------------
# Unicode normalization — fullwidth digits and zero-width characters
# acceptance-findings-1.md §24: "zero-width/fullwidth variants"
# ---------------------------------------------------------------------------


class TestNormalization:
    """Exact captured inputs with Unicode encoding; preservation controls follow."""

    def test_fullwidth_local_phone_removed(self):
        # ０７１２３４５６７８ = fullwidth encoding of 0712345678
        h = _run("Call me at ０７１２３４５６７８", {})
        assert "[phone]" in h.output
        assert "０７１２３４５６７８" not in h.output

    def test_fullwidth_international_phone_removed(self):
        # +２５４７１２３４５６７８ = fullwidth encoding of +254712345678
        h = _run("Number: +２５４７１２３４５６７８", {})
        assert "[phone]" in h.output

    def test_zero_width_space_inside_phone_removed(self):
        # 0712[U+200B]345678 — zero-width space inserted between groups
        h = _run("My number is 0712\u200b345678.", {})
        assert "[phone]" in h.output
        # Neither the ZW-disrupted form nor any fragment should survive as a full number
        assert "0712345678" not in h.output

    def test_zero_width_before_international_prefix_removed(self):
        # +254[U+200B]712345678
        h = _run("Ring +254\u200b712345678 now.", {})
        assert "[phone]" in h.output

    def test_fullwidth_week_number_normalised_not_phone(self):
        # ２４ = fullwidth "24" — normalised to ASCII but NOT a phone prefix
        h = _run("Nina wiki ２４ za ujauzito.", {})
        assert "[phone]" not in h.output
        assert "24" in h.output  # fullwidth normalised to ASCII digit

    def test_zero_width_in_ordinary_text_stripped_not_phone(self):
        # Zero-width in a sentence with no phone number; digits preserved
        h = _run("I am 24\u200b weeks pregnant.", {})
        assert "[phone]" not in h.output
        assert "24" in h.output

    def test_soft_hyphen_stripped_not_phone(self):
        # U+00AD soft hyphen sometimes inserted by keyboards
        h = _run("I am 24\u00ad weeks along.", {})
        assert "[phone]" not in h.output
        assert "24" in h.output


# ---------------------------------------------------------------------------
# Generic + international phone forms
# acceptance-findings-1.md repair-2: "+1 (202) 555-0100" and
# "+44 7700 900123" must become "[phone]".
# Source: evidence/24/repair-1/international-parent-red.log
# ---------------------------------------------------------------------------


class TestInternationalPhone:
    """Exact before/after tests for generic +CC international forms."""

    # --- Exact forms from parent RED log ---

    def test_us_parenthesized_removed(self):
        # exact form from international-parent-red.log
        h = _run("My number is +1 (202) 555-0100", {})
        assert "[phone]" in h.output
        assert "+1 (202) 555-0100" not in h.output

    def test_uk_spaced_removed(self):
        # exact form from international-parent-red.log
        h = _run("+44 7700 900123 also must become [phone]", {})
        assert "[phone]" in h.output
        assert "+44 7700 900123" not in h.output

    # --- Additional +CC forms ---

    def test_us_contiguous_removed(self):
        h = _run("Call +12025550100", {})
        assert "[phone]" in h.output
        assert "+12025550100" not in h.output

    def test_uk_contiguous_removed(self):
        h = _run("Ring +447700900123", {})
        assert "[phone]" in h.output
        assert "+447700900123" not in h.output

    def test_plus_cc_hyphenated_removed(self):
        h = _run("Contact: +1-202-555-0100", {})
        assert "[phone]" in h.output
        assert "+1-202-555-0100" not in h.output

    def test_plus_cc_no_separator_parenthesized_removed(self):
        h = _run("Send to +1(202)5550100", {})
        assert "[phone]" in h.output
        assert "+1(202)5550100" not in h.output

    def test_plus_other_cc_removed(self):
        # +254 still covered by generic + branch
        h = _run("Number: +254712345678", {})
        assert "[phone]" in h.output

    def test_message_text_after_international_preserved(self):
        h = _run("Call +44 7700 900123 for antenatal advice at week 24.", {})
        assert "[phone]" in h.output
        assert "week 24" in h.output
        assert "antenatal advice" in h.output

    # --- Preservation controls: exact inputs that must NOT become [phone] ---

    def test_plus_before_week_number_not_a_phone(self):
        # "+20 weeks" — + then digit(s) then word; too few digit positions
        h = _run("I am +20 weeks pregnant.", {})
        assert "[phone]" not in h.output
        assert "20" in h.output

    def test_plus_year_not_a_phone(self):
        # "+2024" — 4 digits after +, below 6-repetition minimum
        h = _run("Study started in +2024.", {})
        assert "[phone]" not in h.output

    def test_ordinary_text_with_parens_not_a_phone(self):
        # Parentheses in ordinary text must not trigger phone detection
        h = _run("I visited the clinic (Kisumu) last week.", {})
        assert "[phone]" not in h.output
        assert "Kisumu" in h.output

    def test_pregnancy_weeks_with_plus_context_preserved(self):
        h = _run("She is +20 weeks and doing well.", {})
        assert "[phone]" not in h.output
        assert "20 weeks" in h.output
