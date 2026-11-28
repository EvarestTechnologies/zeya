"""
Rules-only mode (issue #26, manual part). A second, reviewed pipeline build with no AI
node at all. Operators publish it as an OCS version when the AI provider fails and
roll back to the normal version afterwards. Questions with no answer card get the
approved fixed reply from knowledge_referral (sign-off C2 and C2a).
"""

import json

from ocs.build_pipeline import COMMITTED_RULES_ONLY_PIPELINE, build_pipeline


def _graph(**kwargs):
    flow = build_pipeline(0, 0, **kwargs)["data"]
    names = {n["id"]: n["data"]["params"]["name"] for n in flow["nodes"]}
    nodes = {n["data"]["params"]["name"]: n for n in flow["nodes"]}
    edges = {(names[e["source"]], names[e["target"]], e["sourceHandle"]) for e in flow["edges"]}
    return nodes, edges


def test_rules_only_build_has_no_ai_node():
    nodes, edges = _graph(rules_only=True)
    assert not [n for n in nodes.values() if n["data"]["type"] == "LLMResponseWithPrompt"]
    for name in ("llm", "llm_input", "prompt_budget", "budget_router"):
        assert name not in nodes
        assert not [e for e in edges if name in e[:2]]


def test_questions_without_a_card_get_the_fixed_reply():
    _, edges = _graph(rules_only=True)
    assert ("answer_router", "knowledge_referral", "output_1") in edges


def test_everything_else_is_the_same_as_the_normal_build():
    normal_nodes, normal_edges = _graph()
    rules_nodes, rules_edges = _graph(rules_only=True)
    ai_only = {"llm", "llm_input", "prompt_budget", "budget_router"}
    assert set(rules_nodes) == set(normal_nodes) - ai_only
    for name in rules_nodes:
        assert rules_nodes[name]["data"] == normal_nodes[name]["data"], name
    kept = {e for e in normal_edges if not (set(e[:2]) & ai_only)}
    assert rules_edges == kept | {("answer_router", "knowledge_referral", "output_1")}


def test_emergency_access_and_registration_paths_are_unchanged():
    _, edges = _graph(rules_only=True)
    for edge in [
        ("danger_router", "emergency_response", "output_0"),
        ("danger_router", "access_gate", "output_1"),
        ("access_router", "registration", "output_2"),
        ("registration_router", "kb_context", "output_1"),
        ("answer_router", "output_guard", "output_0"),
    ]:
        assert edge in edges


def test_rules_only_pipeline_has_its_own_name():
    assert "rules only" in build_pipeline(0, 0, rules_only=True)["name"].lower()


def test_committed_rules_only_pipeline_is_up_to_date():
    expected = json.dumps(build_pipeline(0, 0, rules_only=True), indent=2, ensure_ascii=False) + "\n"
    assert COMMITTED_RULES_ONLY_PIPELINE.read_text() == expected, (
        "Run: python -m ocs.build_pipeline --rules-only --write"
    )


def test_drift_check_accepts_the_rules_only_build(tmp_path):
    from ocs.check_drift import find_drift, main

    live = build_pipeline(7, 31, rules_only=True)
    assert find_drift(live, 7, 31, rules_only=True) == []
    # The normal build is drift when the rules-only version is expected, and the reverse.
    assert find_drift(build_pipeline(7, 31), 7, 31, rules_only=True)
    assert find_drift(live, 7, 31)
    path = tmp_path / "live.json"
    path.write_text(json.dumps(live))
    assert main([str(path), "--llm-provider-id", "7", "--llm-provider-model-id", "31", "--rules-only"]) == 0
