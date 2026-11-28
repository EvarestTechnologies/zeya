"""
The emergency-response node sends Zeya's header and footer around a list of national
emergency numbers, in English and Swahili. Zeya listed five Migori facilities; ZEYA is
open to women anywhere in Kenya, so the OCS message gives numbers that work nationwide
(methodological change 9). It must not depend on the database, the network or the
message text.
"""

import pytest

from app.services.danger_signs import (
    EMERGENCY_RESPONSE_FOOTER_EN,
    EMERGENCY_RESPONSE_FOOTER_SW,
    EMERGENCY_RESPONSE_HEADER_EN,
    EMERGENCY_RESPONSE_HEADER_SW,
)
from ocs.tests.conftest import node_source
from ocs.tests.sandbox import NodeHarness

HEADERS = {"en": EMERGENCY_RESPONSE_HEADER_EN, "sw": EMERGENCY_RESPONSE_HEADER_SW}
FOOTERS = {"en": EMERGENCY_RESPONSE_FOOTER_EN, "sw": EMERGENCY_RESPONSE_FOOTER_SW}

# Every number here must be confirmed by calling it before a release (docs/ocs-migration.md).
NUMBERS = {
    "en": (
        "Emergency numbers:\n"
        "- Ambulance: 922 (free)\n"
        "- Emergency services: 999 or 112\n"
        "- Migori County ambulance: 0740 587 479, 0740 588 519, 0740 588 853 or +254 724 024 296"
    ),
    "sw": (
        "Nambari za dharura:\n"
        "- Ambulensi: 922 (bila malipo)\n"
        "- Huduma za dharura: 999 au 112\n"
        "- Ambulensi ya Kaunti ya Migori: 0740 587 479, 0740 588 519, 0740 588 853 au +254 724 024 296"
    ),
}


def _expected_message(language: str) -> str:
    return HEADERS[language] + NUMBERS[language] + FOOTERS[language]


def _run(participant_data: dict, message: str = "heavy bleeding") -> str:
    return NodeHarness(node_source("emergency_response"), participant_data=participant_data).run(message)


@pytest.mark.parametrize("language", ["en", "sw"])
def test_message_is_zeya_header_national_numbers_and_footer(language):
    assert _run({"language_preference": language}) == _expected_message(language)


@pytest.mark.parametrize("participant_data", [{}, {"language_preference": None}, {"language_preference": "fr"}])
def test_defaults_to_english(participant_data):
    assert _run(participant_data) == _expected_message("en")


@pytest.mark.parametrize("language", ["en", "sw"])
@pytest.mark.parametrize(
    "number", ["999", "112", "922", "0740 587 479", "0740 588 519", "0740 588 853", "+254 724 024 296"]
)
def test_every_national_number_is_listed(language, number):
    assert number in _run({"language_preference": language})


@pytest.mark.parametrize("language", ["en", "sw"])
def test_only_county_line_is_the_ticked_migori_ambulance(language):
    # Sign-off D (28 November 2026): the four Migori County ambulance dispatch numbers,
    # confirmed by Stella Oiro, are shown to every participant on one line.
    reply = _run({"language_preference": language})
    county_lines = [line for line in reply.splitlines() if "Migori" in line]
    assert county_lines == [NUMBERS[language].splitlines()[-1]]


@pytest.mark.parametrize("message", ["", "mtoto hatembei", "x" * 5000], ids=["empty", "swahili", "long"])
def test_output_does_not_depend_on_message(message):
    assert _run({"language_preference": "sw"}, message) == _expected_message("sw")
