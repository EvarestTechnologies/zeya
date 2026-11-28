"""
The danger-signs explainer clip is attached when the danger_signs card is sent
(issue #31, approved by Stella Oiro on 28 November 2026). Fixed behaviour, no AI.
"""

import pytest

from ocs.tests.conftest import node_source
from ocs.tests.sandbox import NodeHarness

CLIP_URL = "https://raw.githubusercontent.com/EvarestTechnologies/zeya/main/media/explainers/zeya_danger_signs.mp4"
CLIP = b"\x00\x00\x00\x20ftypisom-fake-mp4-bytes"


class FakeHttp:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


def _ok():
    return {"status_code": 200, "content": CLIP, "is_success": True, "is_error": False}


def _run(state, http):
    harness = NodeHarness(node_source("attach_explainer"), temp_state=state, http=http)
    return harness, harness.run("card text")


@pytest.mark.parametrize("card", ["danger_signs_en", "danger_signs_sw"])
def test_attaches_the_clip_with_the_danger_signs_card(card):
    http = FakeHttp(_ok())
    harness, out = _run({"answer_route": "CARD", "matched_card": card, "guard_route": "PASS"}, http)
    assert out == "card text"
    assert [url for url, _ in http.calls] == [CLIP_URL]
    assert harness.attachments == [("zeya_danger_signs.mp4", CLIP, "video/mp4")]
    assert "explainer_clip:danger_signs" in harness.message_tags


@pytest.mark.parametrize(
    "state",
    [
        {"answer_route": "CARD", "matched_card": "food_groups_en", "guard_route": "PASS"},
        {"answer_route": "ASK_AI", "guard_route": "PASS"},
        {"answer_route": "CARD", "matched_card": "danger_signs_en", "guard_route": "guard_blocked"},
        {},
    ],
    ids=["other card", "ai answer", "guard blocked", "no state"],
)
def test_no_clip_otherwise(state):
    http = FakeHttp(_ok())
    harness, out = _run(state, http)
    assert out == "card text"
    assert http.calls == []
    assert harness.attachments == []


@pytest.mark.parametrize(
    "http",
    [
        FakeHttp(error=RuntimeError("timeout")),
        FakeHttp({"status_code": 404, "content": "Not Found", "is_success": False, "is_error": True}),
        FakeHttp({"status_code": 200, "content": "not bytes", "is_success": True, "is_error": False}),
    ],
    ids=["exception", "404", "text body"],
)
def test_failed_download_still_sends_the_card_text(http):
    harness, out = _run({"answer_route": "CARD", "matched_card": "danger_signs_sw", "guard_route": "PASS"}, http)
    assert out == "card text"
    assert harness.attachments == []
    assert "explainer_clip:failed" in harness.message_tags
