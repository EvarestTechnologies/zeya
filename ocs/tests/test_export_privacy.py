"""
Unit tests for ocs/export_privacy.py — host-side PII scrubbing helper.

All names, contacts and identifiers are public synthetic fixtures only.
No real participant data is used.

Coverage maps to P01–P12 acceptance clauses. Each test section explicitly
documents which clause(s) it covers and asserts the actual sink value.
"""

import json

import pytest

from ocs.export_privacy import (
    PH_EMAIL,
    PH_ID,
    PH_NAME,
    PH_PHONE,
    gather_participant_names,
    scrub,
)

# ===========================================================================
# Placeholder identity (P02)
# ===========================================================================


def test_placeholder_values_are_fixed():
    """P02: placeholders are deterministic fixed strings."""
    assert PH_NAME == "[NAME]"
    assert PH_PHONE == "[PHONE]"
    assert PH_EMAIL == "[EMAIL]"
    assert PH_ID == "[PERSONAL_ID]"


def test_scrub_is_idempotent():
    """P02: applying scrub twice produces the same result as once."""
    text = "Call Exampleperson at 0712345678 or person@example.test"
    names = frozenset({"Exampleperson"})
    once = scrub(text, names)
    twice = scrub(once, names)
    assert once == twice


def test_scrub_non_string_passthrough():
    """P02: non-string input is returned unchanged (defensive)."""
    assert scrub(None) is None  # type: ignore[arg-type]
    assert scrub(42) == 42  # type: ignore[arg-type]


# ===========================================================================
# Phone scrubbing (P04)
# ===========================================================================


@pytest.mark.parametrize(
    "phone",
    [
        "0712345678",  # Kenya local 07
        "0112345678",  # Kenya local 01
        "+254712345678",  # international +254
        "00254712345678",  # international 00254
        "+254 712 345 678",  # with spaces
        "0712 345 678",  # local with spaces
        "+254-712-345-678",  # with ASCII hyphens
        "+254.712.345.678",  # with dots
        "+254\u00a0712\u2009345\u2014678",  # NBSP + thin space + em dash
        "+\uff12\uff15\uff14\u00a0\uff17\uff10\uff10\u2009\uff10\uff10\uff10\u2014\uff10\uff10\uff11",  # fullwidth
        "0700 000 001",  # 10-digit local with space
        "+254 (700) 000-001",  # parens + hyphen
        "00254 700 000 001",  # 00-prefix with spaces
        "+254****0001",  # masked digits (upstream redaction)
    ],
)
def test_phone_patterns_are_scrubbed(phone):
    """P04: recognised phone formats are replaced with [PHONE]."""
    text = f"Contact {phone}; pregnancy week 24."
    result = scrub(text)
    assert phone not in result, f"phone {phone!r} still in output"
    assert PH_PHONE in result
    assert "pregnancy week 24." in result


@pytest.mark.parametrize(
    "not_phone",
    [
        "20",  # pregnancy weeks — 2 digits, no prefix
        "24",  # pregnancy weeks
        "42",  # pregnancy weeks
        "2026-11-21",  # date — no prefix
        "2027-01-02",  # date — no prefix
        "999",  # emergency helpline — 3 digits, no prefix
        "112",  # emergency helpline
        "116",  # emergency helpline
        "922",  # emergency helpline
        "1199",  # emergency helpline — 4 digits, no prefix
    ],
)
def test_legitimate_numbers_are_not_scrubbed(not_phone):
    """P04 negative: pregnancy weeks, dates, emergency codes are not matched."""
    text = f"See {not_phone} for details."
    assert scrub(text) == text, f"legitimate number {not_phone!r} was incorrectly scrubbed"


def test_phone_not_matched_inside_longer_digit_string():
    """P04: phone pattern does not partially consume larger digit strings."""
    # A 20-digit number with no recognised prefix — should not match phone
    text = "Reference 12345678901234567890 elsewhere."
    assert scrub(text) == text


def test_phone_name_not_matched_as_phone():
    """P04: a BSUID-like identifier (KE.123abc) is not treated as a phone."""
    text = "User KE.publicsynthetic001 sent a message."
    assert scrub(text) == text


# ===========================================================================
# Email scrubbing (P04)
# ===========================================================================


@pytest.mark.parametrize(
    "email",
    [
        "person@example.test",
        "person+trial@sub.example.test",
        "PERSON@EXAMPLE.TEST",  # case-insensitive
        "first.last@domain.co.ke",  # subdomain + TLD
        "user-name@test.org",  # hyphen in local
    ],
)
def test_email_patterns_are_scrubbed(email):
    """P04: recognised email forms are replaced with [EMAIL]."""
    text = f"Contact {email} for details."
    result = scrub(text)
    assert email not in result, f"email {email!r} still in output"
    assert PH_EMAIL in result


def test_email_negative_not_prose():
    """P04 negative: clinical prose and URLs without @ are not email-matched."""
    text = "Visit the clinic at 20 weeks. Call 999 or see example.test for info."
    assert scrub(text) == text


# ===========================================================================
# Personal-ID scrubbing (P04)
# ===========================================================================


@pytest.mark.parametrize(
    ("labelled", "payload"),
    [
        ("ID: 12345678", "12345678"),
        ("ID: 123456", "123456"),
        ("id: 12345678", "12345678"),  # case
        ("ID# 12345678", "12345678"),  # hash variant
        ("ID number 12345678", "12345678"),
        ("id number 12345678", "12345678"),
        ("National ID number is 12345678", "12345678"),
        ("national id 12345678", "12345678"),
        ("national id number 12345678", "12345678"),
        ("kitambulisho 12345678", "12345678"),
        ("kitambulisho: 12345678", "12345678"),
        ("namba ya kitambulisho: 12345678", "12345678"),
        ("passport no: A1234567", "A1234567"),
        ("passport number A1234567", "A1234567"),
        ("PASSPORT NO A1234567", "A1234567"),
    ],
)
def test_labelled_id_scrubbed(labelled, payload):
    """P04: labelled explicit ID forms have their payload replaced with [PERSONAL_ID]."""
    text = labelled + "; week 20."
    result = scrub(text)
    assert payload not in result, f"payload {payload!r} still in {result!r}"
    assert PH_ID in result
    assert "week 20." in result


@pytest.mark.parametrize(
    "text",
    [
        "She is 20 weeks pregnant.",
        "Her gestational age is 24.",
        "Reference number 20261121 in the system.",
        "Planning ANC at 20, 24 or 42 weeks.",
        "passport to health care is important.",  # 'passport' as word, no payload
        "National identity is important for care.",  # label without digit payload
    ],
)
def test_unlabelled_numbers_not_scrubbed(text):
    """P04 negative: unlabelled bare numbers and clinical prose are not matched."""
    assert scrub(text) == text, f"unexpected scrub in: {text!r}"


def test_national_id_too_short_not_matched():
    """P04: national ID payload below 6 digits (e.g. 5 digits) is not matched."""
    text = "ID: 12345"  # 5 digits — below 6-digit minimum
    assert scrub(text) == text


def test_national_id_too_long_not_matched():
    """P04: national ID payload above 10 digits is not matched."""
    text = "ID: 12345678901"  # 11 digits — above 10-digit maximum
    assert scrub(text) == text


def test_passport_without_digit_not_matched():
    """P04: passport payload with no digit is not matched (e.g. all letters)."""
    text = "passport number ABCDEFG"  # no digit in payload
    assert scrub(text) == text


# ===========================================================================
# Name scrubbing (P03)
# ===========================================================================


def test_known_name_from_column_scrubbed():
    """P03: name from Participant Name column is replaced with [NAME]."""
    result = scrub("Exampleperson asked about ANC.", frozenset({"Exampleperson"}))
    assert "Exampleperson" not in result
    assert PH_NAME in result


def test_known_name_case_insensitive():
    """P03: name matching is case-insensitive."""
    result = scrub("exampleperson needs care.", frozenset({"Exampleperson"}))
    assert "exampleperson" not in result
    assert PH_NAME in result


def test_known_name_whole_word_boundary():
    """P03: name is matched at whole-word boundaries only."""
    result = scrub("Examplepersonhood is not Exampleperson.", frozenset({"Exampleperson"}))
    # 'Examplepersonhood' should NOT be matched (name is a prefix, not a whole word)
    assert "Examplepersonhood" in result
    # 'Exampleperson' at end should be matched
    assert result.endswith(f"{PH_NAME}.")


def test_name_not_matched_as_substring_inside_word():
    """P03: 'Ann' name does not match inside 'ANC'."""
    result = scrub("Planning ANC at 20 weeks.", frozenset({"Ann"}))
    assert "ANC" in result  # ANC must be preserved
    assert result == "Planning ANC at 20 weeks."


def test_no_name_means_no_name_scrubbing():
    """P03: empty names frozenset means no name substitution (not all participants have names)."""
    text = "Exampleperson asked a question."
    assert scrub(text, frozenset()) == text


def test_compound_name_whitespace_variation():
    """P03: compound name matches with minor whitespace variation."""
    result = scrub("Contact Example  Person today.", frozenset({"Example Person"}))
    assert "Example" not in result or "Person" not in result  # whole name matched
    assert PH_NAME in result


def test_longer_name_matched_first():
    """P03: when both 'Example' and 'Example Person' are names, compound matched first."""
    names = frozenset({"Example", "Example Person"})
    result = scrub("Example Person is here.", names)
    # Compound should be one [NAME], not two separate [NAME] [NAME]
    assert result.count(PH_NAME) == 1


def test_no_cross_participant_names():
    """P03: names from participant A are not applied to participant B's text."""
    # This is verified by the caller (convert_ocs_export passes per-participant names),
    # but we confirm scrub only uses the names provided to it.
    text = "Exampleperson asks about ANC."
    # Participant B has no saved name — text unmodified
    assert scrub(text, frozenset()) == text


# ===========================================================================
# Non-matching bytes preserved (P04/P06)
# ===========================================================================


def test_non_pii_text_preserved_exactly():
    """P04/P06: legitimate text outside matched spans is preserved byte-for-byte."""
    text = "Planning ANC at 20, 24 or 42 weeks; 2026-11-21 and 2027-01-02. Call 999, 112 or 116."
    assert scrub(text, frozenset({"Ann"})) == text


def test_mixed_pii_and_legitimate_text():
    """P04: mixed text — PII replaced, surrounding text preserved exactly."""
    text = "Dear Exampleperson, call 0712345678 or email person@example.test for week 20 care."
    result = scrub(text, frozenset({"Exampleperson"}))
    assert PH_NAME in result
    assert PH_PHONE in result
    assert PH_EMAIL in result
    assert "0712345678" not in result
    assert "person@example.test" not in result
    assert "Exampleperson" not in result
    assert "for week 20 care." in result


# ===========================================================================
# gather_participant_names (P03)
# ===========================================================================


def _make_row(pid: str, name: str = "", saved_name: str = "") -> dict:
    data = {"consent_given": True, "study_participant": True}
    if saved_name:
        data["name"] = saved_name
    return {
        "Participant Public ID": pid,
        "Participant Name": name,
        "Participant Data": json.dumps(data),
    }


def test_gather_names_from_column():
    """P03: name from Participant Name column is gathered."""
    rows = [_make_row("p1", name="Exampleperson")]
    result = gather_participant_names(rows)
    assert result == {"p1": frozenset({"Exampleperson"})}


def test_gather_names_from_data():
    """P03: name from data.name in Participant Data JSON is gathered."""
    rows = [_make_row("p1", saved_name="Exampleperson")]
    result = gather_participant_names(rows)
    assert result == {"p1": frozenset({"Exampleperson"})}


def test_gather_names_both_sources_union():
    """P03: names from both sources are combined in a frozenset."""
    rows = [_make_row("p1", name="Alice", saved_name="Alice Ochieng")]
    result = gather_participant_names(rows)
    assert result["p1"] == frozenset({"Alice", "Alice Ochieng"})


def test_gather_names_per_participant_isolation():
    """P03: names from participant A are not mixed with participant B's names."""
    rows = [_make_row("p1", name="Alice"), _make_row("p2", name="Bob")]
    result = gather_participant_names(rows)
    assert result["p1"] == frozenset({"Alice"})
    assert result["p2"] == frozenset({"Bob"})


def test_gather_names_later_row_missing_still_uses_earlier():
    """P03: earlier name persists for a participant whose later rows lack name metadata."""
    rows = [
        _make_row("p1", saved_name="Exampleperson"),  # row 1: has name
        _make_row("p1"),  # row 2: no name
    ]
    result = gather_participant_names(rows)
    assert "Exampleperson" in result["p1"]


def test_gather_names_empty_name_not_included():
    """P03: empty-string name fields are not included in the frozenset."""
    rows = [_make_row("p1", name="", saved_name="")]
    result = gather_participant_names(rows)
    assert result.get("p1", frozenset()) == frozenset()


def test_gather_names_malformed_json_skipped():
    """P03: malformed Participant Data JSON is silently skipped."""
    row = {
        "Participant Public ID": "p1",
        "Participant Name": "Alice",
        "Participant Data": "{not json",
    }
    result = gather_participant_names([row])
    assert result["p1"] == frozenset({"Alice"})


def test_gather_names_missing_pid_skipped():
    """P03: rows without Participant Public ID are skipped."""
    row = {"Participant Name": "Alice", "Participant Data": "{}"}
    result = gather_participant_names([row])
    assert result == {}


# ===========================================================================
# Danger keywords preserve category order (P05)
# ===========================================================================


def test_danger_keywords_phone_in_payload_scrubbed():
    """P05: phone number embedded in a danger keyword payload is scrubbed."""
    result = scrub("bleeding 0712345678, headache", frozenset())
    assert "0712345678" not in result
    assert PH_PHONE in result
    assert "bleeding" in result
    assert "headache" in result


def test_danger_keywords_email_in_payload_scrubbed():
    """P05: email embedded in danger keyword payload is scrubbed."""
    result = scrub("headache person@example.test, bleeding", frozenset())
    assert "person@example.test" not in result
    assert PH_EMAIL in result
    assert "headache" in result


def test_danger_keywords_category_text_preserved():
    """P05: clinical category text (e.g. 'bleeding', 'headache') is preserved."""
    result = scrub("bleeding +254****0001, headache person@test.com", frozenset())
    assert "bleeding" in result
    assert "headache" in result
    assert PH_PHONE in result
    assert PH_EMAIL in result


# ===========================================================================
# C1 regression — Phone boundary and Unicode forms (P04)
# ===========================================================================


@pytest.mark.parametrize(
    "phone",
    [
        "254700000001",  # bare Kenya country code (12 digits)
        "+\u0662\u0665\u0664 \u0667\u0660\u0660 \u0660\u0660\u0660 \u0660\u0660\u0661",  # Arabic-Indic +٢٥٤ ٧٠٠ ٠٠٠ ٠٠١
        "\uff10\uff17\uff10\uff10 \uff10\uff10\uff10 \uff10\uff10\uff11",  # fullwidth ０７００ ０００ ００１
    ],
)
def test_required_additional_phone_forms_replaced(phone):
    """C1: bare country code and Unicode digit phone forms must be replaced."""
    text = f"Call {phone}; week 24."
    result = scrub(text)
    assert phone not in result, f"phone {phone!r} still in output"
    assert PH_PHONE in result
    assert "week 24." in result


@pytest.mark.parametrize(
    "text",
    [
        "Call +254****0001. Then attend ANC.",
        "Call +254****0001 (then attend ANC).",
    ],
)
def test_masked_phone_does_not_consume_surrounding_punctuation(text):
    """C1: masked phone replaced, trailing . and ( not consumed."""
    result = scrub(text)
    expected = text.replace("+254****0001", PH_PHONE)
    assert result == expected, f"unexpected: {result!r}"


@pytest.mark.parametrize(
    "text",
    [
        "Appointment 01-02-2027.",  # date with 01 prefix — 8 digits
        "Appointment 07-11-2026.",  # date with 07 prefix — 8 digits
        "Reference +1234567890123456789012345 remains unsupported.",  # 25 digits > 15
        "BSUID KE.07123456789012345678 remains unchanged.",  # preceded by dot
    ],
)
def test_phone_boundaries_no_overbroad_match(text):
    """C1: dates, overlong and BSUID-adjacent digit strings are not phone-matched."""
    assert scrub(text) == text, f"unexpected scrub in: {text!r}"


# ===========================================================================
# C2 regression — ID label and payload exact replacement (P04)
# ===========================================================================


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ID:12345678", "ID:" + PH_ID),
        ("ID#12345678", "ID#" + PH_ID),
        ("ID 12345678", "ID " + PH_ID),
        ("ID: 12345678", "ID: " + PH_ID),
    ],
)
def test_id_separator_variants_exact_replacement(text, expected):
    """C2: colon/hash/equals/space separator forms produce exact label+sep bytes."""
    assert scrub(text) == expected


def test_id_label_not_matched_inside_word():
    """C2: 'id' suffix in 'valid' must not trigger ID label match."""
    assert scrub("valid: 12345678") == "valid: 12345678"


def test_id_payload_alpha_suffix_not_matched():
    """C2: payload with alphanumeric suffix (ID: 12345678a) is not matched."""
    assert scrub("ID: 12345678a") == "ID: 12345678a"


def test_id_separator_bytes_preserved_exactly():
    """C2: exact whitespace/separator chars between label and payload are preserved."""
    text = "passport no:\tA1234567; National ID number is 12345678."
    expected = "passport no:\t" + PH_ID + "; National ID number is " + PH_ID + "."
    assert scrub(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ID number 0700000001", "ID number " + PH_ID),  # numeric ID, not phone
        ("passport no: 0700000001", "passport no: " + PH_ID),  # numeric passport, not phone
    ],
)
def test_labelled_numeric_id_takes_precedence_over_phone(text, expected):
    """C2/OOB: labelled ID scrubbing runs before phone scrubbing; numeric payload
    under an explicit label becomes [PERSONAL_ID], not [PHONE].
    """
    assert scrub(text) == expected, f"got: {scrub(text)!r}"


# ===========================================================================
# C3 regression — Idempotency with placeholder-name collision (P02)
# ===========================================================================


@pytest.mark.parametrize("name", ["NAME", "PHONE", "EMAIL", "PERSONAL_ID"])
def test_placeholder_tokens_stable_under_saved_name_collision(name):
    """C3: existing [PLACEHOLDER] tokens are not modified when the saved name
    matches a placeholder keyword.  Scrub is idempotent for these cases.
    """
    original = "[NAME] [PHONE] [EMAIL] [PERSONAL_ID]"
    once = scrub(original, frozenset({name}))
    assert once == original, f"placeholder [{name}] was rewritten: {once!r}"
    assert scrub(once, frozenset({name})) == original


# ===========================================================================
# F1 regression — Numeric email local part not consumed as phone (P04)
# ===========================================================================


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Contact 0712345678@example.test for info",
            "Contact [EMAIL] for info",
        ),
        (
            "Sending to 0712345678@example.test",
            "Sending to [EMAIL]",
        ),
        (
            "Call +254700000001 or email 0712345678@example.test",
            "Call [PHONE] or email [EMAIL]",
        ),
    ],
)
def test_numeric_email_local_part_becomes_email_not_phone(text, expected):
    """F1: a numeric local part (0712345678@...) must produce [EMAIL], not
    [PHONE]@domain.  Emails run before phones in application order.
    """
    assert scrub(text) == expected


# ===========================================================================
# F2 regression — Phone dot separator is conservative (P04/P06)
# ===========================================================================


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Call 0712345678. 20 weeks.",
            "Call [PHONE]. 20 weeks.",
        ),
        (
            "Call 0712345678. 1 day.",
            "Call [PHONE]. 1 day.",
        ),
        (
            "Call 0712345678. 12 kg.",
            "Call [PHONE]. 12 kg.",
        ),
    ],
)
def test_phone_sentence_period_not_consumed(text, expected):
    """F2: a sentence period followed by a space is NOT consumed as a phone
    separator.  The trailing '. N' remains in the output exactly.
    """
    assert scrub(text) == expected, f"got: {scrub(text)!r}"


@pytest.mark.parametrize(
    "phone",
    [
        "+254.700.000.001",  # dot-delimited international
        "+254.712.345.678",  # another dot form
    ],
)
def test_dotted_phone_still_replaced(phone):
    """F2 positive: dot is accepted as separator when immediately before a digit;
    dotted phone forms continue to produce [PHONE].
    """
    text = f"Call {phone} today."
    result = scrub(text)
    assert phone not in result, f"phone {phone!r} not replaced: {result!r}"
    assert PH_PHONE in result


# ===========================================================================
# F3 regression — Passport is/ni connector (P04)
# ===========================================================================


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("passport no is A1234567", "passport no is " + PH_ID),
        ("passport number is B9876543", "passport number is " + PH_ID),
        ("passport number ni C1122334", "passport number ni " + PH_ID),
        ("passport ni A1234567", "passport ni " + PH_ID),
        ("My passport ni D5566778 for travel", "My passport ni " + PH_ID + " for travel"),
    ],
)
def test_passport_is_ni_connector(text, expected):
    """F3: passport label with 'is'/'ni' connector replaces payload and preserves
    label+separator bytes exactly.
    """
    assert scrub(text) == expected, f"got: {scrub(text)!r}"


# ===========================================================================
# F4 regression — Bracketed names scrubbed; reserved tokens protected (P02/P03)
# ===========================================================================


@pytest.mark.parametrize(
    ("text", "names", "expected"),
    [
        (
            "[Exampleperson] needs care",
            frozenset({"Exampleperson"}),
            "[[NAME]] needs care",
        ),
        (
            "[Exampleperson] is confirmed",
            frozenset({"Exampleperson"}),
            "[[NAME]] is confirmed",
        ),
        (
            "Exampleperson asked about [Exampleperson]",
            frozenset({"Exampleperson"}),
            "[NAME] asked about [[NAME]]",
        ),
    ],
)
def test_bracketed_name_is_replaced(text, names, expected):
    """F4: a name inside brackets (not a reserved placeholder) is matched and
    replaced; the outer brackets are preserved.
    """
    assert scrub(text, names) == expected, f"got: {scrub(text, names)!r}"


@pytest.mark.parametrize(
    ("text", "names"),
    [
        ("[NAME] text", frozenset({"NAME"})),
        ("[PHONE] text", frozenset({"PHONE"})),
        ("[EMAIL] text", frozenset({"EMAIL"})),
        ("[PERSONAL_ID] text", frozenset({"PERSONAL_ID"})),
    ],
)
def test_reserved_placeholder_tokens_not_modified_by_name_pass(text, names):
    """F4: the four reserved placeholder tokens are never modified by the name
    substitution pass, even when the saved name matches the token keyword exactly.
    """
    assert scrub(text, names) == text, f"got: {scrub(text, names)!r}"


def test_bracket_name_idempotent():
    """F4: scrub applied twice to output containing [[NAME]] is idempotent."""
    names = frozenset({"Exampleperson"})
    once = scrub("[Exampleperson] needs care", names)
    assert once == "[[NAME]] needs care"
    twice = scrub(once, names)
    assert twice == once


# ===========================================================================
# F5 regression — Arabic-Indic Kenya-local 07/01 prefix (P04)
# ===========================================================================


@pytest.mark.parametrize(
    ("phone", "label"),
    [
        ("\u0660\u0667\u0660\u0660 \u0660\u0660\u0660 \u0660\u0660\u0661", "Arabic-Indic ٠٧٠٠ ٠٠٠ ٠٠١"),
        ("\u0660\u0661\u0660\u0660 \u0660\u0660\u0660 \u0660\u0660\u0661", "Arabic-Indic ٠١٠٠ ٠٠٠ ٠٠١"),
    ],
)
def test_arabic_indic_local_phone_replaced(phone, label):
    """F5: Arabic-Indic Kenya-local 07/01 prefix phones must become [PHONE]."""
    text = f"My number is {phone}; week 24."
    result = scrub(text)
    assert phone not in result, f"{label} not replaced: {result!r}"
    assert PH_PHONE in result
    assert "week 24." in result


# ===========================================================================
# F6 regression — Deterministic output across PYTHONHASHSEED (P02)
# ===========================================================================


def test_equal_length_name_ordering_is_deterministic():
    """F6: when two saved names have the same length, the lexicographic tie-break
    ensures the same name is applied first across all PYTHONHASHSEED values.
    Alpha Beta Gamma with names {Alpha Beta, Beta Gamma} must always yield
    '[NAME] Gamma' (Alpha Beta consumed first, alphabetically earlier).
    """
    names = frozenset({"Alpha Beta", "Beta Gamma"})
    text = "Alpha Beta Gamma"
    result = scrub(text, names)
    assert result == "[NAME] Gamma", f"got: {result!r}"


def test_determinism_via_subprocesses():
    """F6 subprocess proof: same result across PYTHONHASHSEED 1-8 without relying
    on same-process frozenset ordering.
    """
    import os
    import subprocess
    import sys

    code = (
        "from ocs.export_privacy import scrub; "
        "print(scrub('Alpha Beta Gamma', frozenset({'Alpha Beta', 'Beta Gamma'})))"
    )
    from pathlib import Path

    root = str(Path(__file__).resolve().parents[2])  # repository root
    results = set()
    for seed in range(1, 9):
        env = {**os.environ, "PYTHONHASHSEED": str(seed), "PYTHONPATH": root}
        out = subprocess.check_output([sys.executable, "-c", code], env=env, cwd=root).decode().strip()
        results.add(out)
    assert len(results) == 1, f"Non-deterministic across seeds: {results}"
    assert next(iter(results)) == "[NAME] Gamma"


# ===========================================================================
# Sentinel-collision regressions (P02/P03) — RED before fix, then GREEN
# ===========================================================================


@pytest.mark.parametrize(
    ("text", "names", "expected"),
    [
        # saved name 'S1' collides with old NUL sentinel for [PHONE]
        ("[PHONE]", frozenset({"S1"}), "[PHONE]"),
        # saved name 'S2' collides with old NUL sentinel for [EMAIL]
        ("[EMAIL]", frozenset({"S2"}), "[EMAIL]"),
        # saved name 'S0' collides with old NUL sentinel for [NAME]
        ("[NAME]", frozenset({"S0"}), "[NAME]"),
        # saved name 'S3' collides with old NUL sentinel for [PERSONAL_ID]
        ("[PERSONAL_ID]", frozenset({"S3"}), "[PERSONAL_ID]"),
        # all four at once — none should change
        (
            "[NAME] [PHONE] [EMAIL] [PERSONAL_ID]",
            frozenset({"S0", "S1", "S2", "S3"}),
            "[NAME] [PHONE] [EMAIL] [PERSONAL_ID]",
        ),
    ],
)
def test_saved_name_matching_sentinel_string_does_not_corrupt_placeholder(text, names, expected):
    """P02/P03 regression: a participant whose saved name happens to be 'S0',
    'S1', 'S2', or 'S3' must not corrupt existing placeholder tokens.  The
    old NUL-sentinel approach used '\x00S1\x00' etc. as temporaries, which
    made those exact ASCII strings special.  Structural protection removes
    any reserved-character dependency.
    """
    result = scrub(text, names)
    assert result == expected, f"placeholder corrupted by saved name {names!r}: expected {expected!r}, got {result!r}"


def test_raw_nul_sentinel_bytes_in_input_preserved_unchanged():
    """P02 regression: literal NUL bytes in input text must be preserved
    byte-for-byte when no saved names are provided.  The old sentinel
    approach restored '\x00S0\x00' → '[NAME]' unconditionally, corrupting
    any input that happened to contain those bytes.
    """
    text = "ordinary \x00S0\x00 bytes"
    result = scrub(text, frozenset())
    assert result == text, f"NUL bytes in input were corrupted: {result!r}"


def test_raw_nul_bytes_preserved_with_unrelated_saved_name():
    """P02 regression: NUL bytes in input must not be restored as placeholders
    even when unrelated saved names are present and applied.
    """
    text = "ordinary \x00S0\x00 bytes and Exampleperson"
    result = scrub(text, frozenset({"Exampleperson"}))
    assert "\x00S0\x00" in result, f"NUL bytes were lost: {result!r}"
    assert "[NAME]" in result  # Exampleperson replaced
    assert "[PHONE]" not in result
