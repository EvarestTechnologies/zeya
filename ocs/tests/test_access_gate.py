"""
Access gate (issue #21). Only approved testers get past it, and images or files get
a fixed reply, so nothing but an approved tester's text reaches the AI. Fixed replies,
no AI. The danger gate still runs first, so emergencies are answered for everyone.
"""

import pytest

from ocs.build_pipeline import build_pipeline
from ocs.tests.conftest import node_source
from ocs.tests.sandbox import NodeHarness

NOT_TESTER_EN = (
    "Zeya is being tested and is not open to the public yet. For pregnancy questions, "
    "please ask your health worker. In an emergency, call 922, free from any phone."
)
NOT_TESTER_SW = (
    "Zeya inafanyiwa majaribio na bado haijafunguliwa kwa umma. Kwa maswali ya ujauzito, "
    "tafadhali muulize muhudumu wa afya. Kwa dharura, piga 922 bila malipo."
)
MEDIA_EN = "I can only read text messages for now. Please type your question in words."
MEDIA_SW = "Kwa sasa ninaweza kusoma ujumbe wa maandishi pekee. Tafadhali andika swali lako kwa maneno."
PHOTO = [{"file_id": 1, "type": "image", "name": "photo.jpg"}]


def _run(participant_data, attachments=None, message="What should I eat?"):
    state = {"attachments": attachments} if attachments is not None else {}
    harness = NodeHarness(node_source("access_gate"), temp_state=state, participant_data=participant_data)
    return harness, harness.run(message)


def test_approved_tester_text_passes_unchanged():
    harness, out = _run({"approved_tester": True, "language_preference": "en"}, [])
    assert out == "What should I eat?"
    assert harness.temp_state["access_route"] == "OK"
    assert "route:access_ok" in harness.message_tags


@pytest.mark.parametrize(
    "data",
    [{}, {"approved_tester": False}, {"approved_tester": "true"}, {"approved_tester": 1}, {"study_participant": True}],
    ids=["no data", "false", "string true", "number one", "study flag only"],
)
def test_anyone_not_explicitly_approved_gets_the_fixed_reply(data):
    harness, out = _run(data)
    assert harness.temp_state["access_route"] == "NOT_TESTER"
    assert out == NOT_TESTER_EN + "\n\n" + NOT_TESTER_SW
    assert "route:access_not_tester" in harness.message_tags


@pytest.mark.parametrize(("language", "expected"), [("en", NOT_TESTER_EN), ("sw", NOT_TESTER_SW)])
def test_not_tester_reply_follows_a_saved_language(language, expected):
    _, out = _run({"language_preference": language})
    assert out == expected


@pytest.mark.parametrize(("language", "expected"), [("en", MEDIA_EN), ("sw", MEDIA_SW)])
def test_tester_sending_a_file_gets_the_media_reply(language, expected):
    harness, out = _run({"approved_tester": True, "language_preference": language}, PHOTO, message="")
    assert harness.temp_state["access_route"] == "MEDIA"
    assert out == expected
    assert "route:access_media" in harness.message_tags


def test_media_reply_without_a_language_is_bilingual():
    _, out = _run({"approved_tester": True}, PHOTO, message="")
    assert out == MEDIA_EN + "\n\n" + MEDIA_SW


def test_non_tester_with_a_file_gets_the_not_tester_reply():
    harness, _ = _run({}, PHOTO)
    assert harness.temp_state["access_route"] == "NOT_TESTER"


def test_the_message_text_is_never_echoed_back():
    secret = "my number is 0712345678"
    for data, attachments in [({}, None), ({"approved_tester": True}, PHOTO)]:
        _, out = _run(data, attachments, message=secret)
        assert secret not in out


# ----------------------------------------------------------------- pipeline wiring


def _graph():
    flow = build_pipeline(0, 0)["data"]
    names = {n["id"]: n["data"]["params"]["name"] for n in flow["nodes"]}
    edges = [(names[e["source"]], names[e["target"]], e["sourceHandle"]) for e in flow["edges"]]
    nodes = {n["data"]["params"]["name"]: n for n in flow["nodes"]}
    return nodes, edges


def _reachable(start, edges):
    seen, stack = set(), [start]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(t for s, t, _ in edges if s == current)
    return seen


def test_safe_route_goes_to_the_access_gate_first():
    _, edges = _graph()
    assert ("danger_router", "access_gate", "output_1") in edges
    assert ("access_gate", "access_router", "output") in edges
    assert ("danger_router", "registration", "output_1") not in edges


def test_access_router_fails_closed():
    nodes, edges = _graph()
    params = nodes["access_router"]["data"]["params"]
    assert params["data_source"] == "temp_state"
    assert params["route_key"] == "access_route"
    assert params["keywords"] == ["NOT_TESTER", "MEDIA", "OK"]
    assert params["keywords"][params["default_keyword_index"]] == "NOT_TESTER"
    assert ("access_router", "registration", "output_2") in edges


@pytest.mark.parametrize("handle", ["output_0", "output_1"], ids=["NOT_TESTER", "MEDIA"])
def test_refused_routes_never_reach_the_ai(handle):
    nodes, edges = _graph()
    (target,) = [t for s, t, h in edges if s == "access_router" and h == handle]
    branch = _reachable(target, edges)
    assert "llm" not in branch
    assert "registration" not in branch
    assert "end" in branch
