"""
The fixed line sent before answers to danger-sign questions (work order task 6,
sign-off A4 (c)). Written in advance; no AI is involved.
"""

import re

import pytest

from ocs.tests.conftest import node_source
from ocs.tests.sandbox import NodeHarness

LINE_EN = "If this is happening to you now, go to a health facility now."
LINE_SW = "Kama hili linakutokea sasa, nenda kituo cha afya sasa hivi."


def _run(message, question, language="en"):
    harness = NodeHarness(
        node_source("danger_question_line"),
        temp_state={"danger_question": question},
        participant_data={"language_preference": language},
    )
    return harness, harness.run(message)


def test_no_line_when_not_a_danger_question():
    harness, out = _run("Eat one extra meal every day.", False)
    assert out == "Eat one extra meal every day."
    assert harness.message_tags == []


def test_no_line_when_gate_did_not_set_the_key():
    harness = NodeHarness(node_source("danger_question_line"), participant_data={"language_preference": "en"})
    assert harness.run("reply") == "reply"


def test_english_line_comes_first_then_the_answer():
    harness, out = _run("Danger signs in pregnancy: ...", True)
    assert out.startswith(LINE_EN)
    assert out.endswith("\n\nDanger signs in pregnancy: ...")
    assert "danger_question_line" in harness.message_tags


def test_swahili_line_for_swahili_participants():
    _, out = _run("Jibu", True, "sw")
    assert out.startswith(LINE_SW)
    assert out.endswith("\n\nJibu")


@pytest.mark.parametrize("language", ["en", "sw"])
def test_line_lists_only_the_numbers_in_the_emergency_reply(language):
    _, out = _run("answer", True, language)
    line = out.split("\n\n")[0]
    emergency = NodeHarness(node_source("emergency_response"), participant_data={"language_preference": language})
    reply = emergency.run("x")
    numbers = re.findall(r"\+?\d[\d ]{1,}\d", line)
    assert numbers, "the fixed line must give the verified numbers"
    for number in numbers:
        assert number in reply, f"{number!r} is in the fixed line but not in the emergency reply"
