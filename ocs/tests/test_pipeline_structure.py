"""
Structural guarantees of the generated OCS pipeline.

These tests read the pipeline as a graph and check that the danger gate is the
only way in, that the emergency branch has no LLM node, and that every LLM node
can only be reached through the router's SAFE handle.
"""

import json

import pytest

from ocs.build_pipeline import COMMITTED_PIPELINE, SYSTEM_PROMPT_FILE, build_pipeline
from ocs.tests.conftest import NODES

# Every OCS node type that calls an LLM (apps/pipelines/nodes/nodes.py).
LLM_NODE_TYPES = {
    "LLMResponse",
    "LLMResponseWithPrompt",
    "RouterNode",
    "AssistantNode",
    "ExtractStructuredData",
    "ExtractParticipantData",
}


@pytest.fixture(scope="module")
def pipeline():
    return build_pipeline(llm_provider_id=1, llm_provider_model_id=2)


@pytest.fixture(scope="module")
def graph(pipeline):
    nodes = {n["id"]: n for n in pipeline["data"]["nodes"]}
    edges = pipeline["data"]["edges"]
    return nodes, edges


def _by_name(nodes, name):
    matches = [n for n in nodes.values() if n["data"]["params"]["name"] == name]
    assert len(matches) == 1, name
    return matches[0]


def _is_llm(node) -> bool:
    return node["data"]["type"] in LLM_NODE_TYPES or "llm_provider_id" in node["data"]["params"]


def _reachable(start_id, edges, skip=lambda edge: False):
    seen, stack = set(), [start_id]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(e["target"] for e in edges if e["source"] == current and not skip(e))
    return seen


def _outgoing(node_id, edges):
    return [e for e in edges if e["source"] == node_id]


def test_starts_with_gate_then_router(graph):
    nodes, edges = graph
    start = next(n for n in nodes.values() if n["type"] == "startNode")
    gate = _by_name(nodes, "danger_gate")
    router = _by_name(nodes, "danger_router")

    assert [e["target"] for e in _outgoing(start["id"], edges)] == [gate["id"]]
    assert [e["target"] for e in _outgoing(gate["id"], edges)] == [router["id"]]
    assert [e["source"] for e in edges if e["target"] == gate["id"]] == [start["id"]]


def test_danger_router_config(graph):
    nodes, _ = graph
    params = _by_name(nodes, "danger_router")["data"]["params"]

    assert _by_name(nodes, "danger_router")["data"]["type"] == "StaticRouterNode"
    assert params["data_source"] == "temp_state"
    assert params["route_key"] == "danger_route"
    assert params["keywords"] == ["EMERGENCY", "SAFE"]
    # A missing or unexpected route value falls to EMERGENCY, never to the LLM.
    assert params["keywords"][params["default_keyword_index"]] == "EMERGENCY"


def test_emergency_branch_has_no_llm(graph):
    nodes, edges = graph
    router = _by_name(nodes, "danger_router")
    (emergency_edge,) = [e for e in _outgoing(router["id"], edges) if e["sourceHandle"] == "output_0"]

    branch = _reachable(emergency_edge["target"], edges)

    assert _by_name(nodes, "emergency_response")["id"] in branch
    assert not [nodes[i]["data"]["params"]["name"] for i in branch if _is_llm(nodes[i])]


def test_llm_reachable_only_through_safe(graph):
    nodes, edges = graph
    start = next(n for n in nodes.values() if n["type"] == "startNode")
    router = _by_name(nodes, "danger_router")
    llm_ids = {i for i, n in nodes.items() if _is_llm(n)}
    assert llm_ids, "expected at least one LLM node"

    def is_safe_edge(edge):
        return edge["source"] == router["id"] and edge["sourceHandle"] == "output_1"

    assert not llm_ids & _reachable(start["id"], edges, skip=is_safe_edge)


def test_every_node_is_downstream_of_router(graph):
    nodes, edges = graph
    start = next(n for n in nodes.values() if n["type"] == "startNode")
    gate = _by_name(nodes, "danger_gate")
    router = _by_name(nodes, "danger_router")

    assert set(nodes) == {start["id"], gate["id"]} | _reachable(router["id"], edges)


def test_registration_router_defaults_away_from_llm(graph):
    """REGISTERED route must go to kb_context (source selection), not directly to the LLM.

    The full registered path is:
        registration_router (output_1=REGISTERED)
        -> kb_context -> kb_router
            FALSE -> knowledge_referral -> end   (no model call)
            TRUE  -> answer_match -> answer_router
                CARD   -> output_guard -> end
                ASK_AI -> llm_input -> llm -> output_guard -> end

    The LLM is never the first stop after registration.
    """
    nodes, edges = graph
    router = _by_name(nodes, "registration_router")
    params = router["data"]["params"]
    kb_ctx = _by_name(nodes, "kb_context")

    assert params["data_source"] == "temp_state"
    assert params["route_key"] == "registration_route"
    assert params["keywords"] == ["REPLY", "REGISTERED"]
    # Default is REPLY (output_0 → end): unrecognised route ends the turn without LLM.
    assert params["keywords"][params["default_keyword_index"]] == "REPLY"
    # REGISTERED (output_1) must route to knowledge context selection, not the LLM directly.
    (registered_edge,) = [e for e in _outgoing(router["id"], edges) if e["sourceHandle"] == "output_1"]
    assert registered_edge["target"] == kb_ctx["id"], (
        "REGISTERED path must route through knowledge context selection before any LLM call; "
        f"got target {registered_edge['target']!r}"
    )


@pytest.mark.parametrize("name", ["danger_gate", "emergency_response", "registration"])
def test_code_nodes_match_repository_sources(graph, name):
    nodes, _ = graph
    node = _by_name(nodes, name)

    assert node["data"]["type"] == "CodeNode"
    assert node["data"]["params"]["code"] == (NODES / f"{name}.py").read_text()


def test_system_prompt_is_template_based():
    # The grounded prompt uses OCS template variables for KB content and context;
    # it is no longer a verbatim copy of the Zeya backend prompt.
    prompt = SYSTEM_PROMPT_FILE.read_text()
    assert "{temp_state.kb_section}" in prompt
    assert "{temp_state.llm_context}" in prompt


def test_llm_node_provider_ids(graph):
    nodes, _ = graph
    params = _by_name(nodes, "llm")["data"]["params"]
    assert params["llm_provider_id"] == 1
    assert params["llm_provider_model_id"] == 2


# ---------------------------------------------------------------------------
# Phase A: history, temperature, tools, prompt structure, prompt tightening
# Source contract: docs/review/system-prompt.md; OCS engine mixins.py 222-241
# ---------------------------------------------------------------------------


def test_llm_node_no_history(graph):
    """history_type=none prevents historical participant names/phones reaching the model.

    Source: apps/pipelines/nodes/mixins.py:222-241 — history_is_disabled returns []
    for PipelineChatHistoryTypes.NONE; build_history_middleware returns None;
    save_history skips persistence.
    """
    nodes, _ = graph
    params = _by_name(nodes, "llm")["data"]["params"]
    assert params.get("history_type") == "none", (
        f"history_type must be 'none' (got {params.get('history_type')!r}). "
        "Historical messages are not re-sanitized by llm_input; disabling history "
        "is the only supported way to prevent prior PII reaching the model context."
    )
    assert "history_mode" not in params, "history_mode must not be present when history_type='none'"
    assert "max_history_length" not in params, "max_history_length must not be present when history_type='none'"


def test_llm_node_temperature_bounded(graph):
    """LLM temperature must be <= 0.3 for conservative, source-grounded responses."""
    nodes, _ = graph
    params = _by_name(nodes, "llm")["data"]["params"]
    model_params = params.get("llm_model_parameters", {})
    temp = model_params.get("temperature")
    assert temp is not None, "temperature must be explicitly set in llm_model_parameters"
    assert isinstance(temp, (int, float)) and not isinstance(temp, bool), f"temperature must be a number, got {temp!r}"
    assert temp <= 0.3, f"temperature must be <= 0.3 for KB-grounded responses, got {temp}"


def test_llm_node_no_tools(graph):
    """LLM node must not have tools configured (parent controls routing)."""
    nodes, _ = graph
    params = _by_name(nodes, "llm")["data"]["params"]
    assert "tools" not in params, "LLM node must not configure tools"
    assert "agent_tools" not in params, "LLM node must not configure agent_tools"


def test_prompt_is_read_directly_from_system_prompt_file(graph):
    """Prompt must be system_prompt.txt verbatim; llm_context must not be appended.

    system_prompt.txt already embeds {temp_state.llm_context}; appending it again
    would inject the context string twice per turn.
    """
    nodes, _ = graph
    params = _by_name(nodes, "llm")["data"]["params"]
    assert params["prompt"] == SYSTEM_PROMPT_FILE.read_text(), (
        "LLM prompt must equal SYSTEM_PROMPT_FILE.read_text() with no suffix appended. "
        "The {temp_state.llm_context} placeholder is already inside system_prompt.txt."
    )


def test_prompt_placeholders_appear_exactly_once(graph):
    """Each OCS template placeholder must appear exactly once."""
    nodes, _ = graph
    prompt = _by_name(nodes, "llm")["data"]["params"]["prompt"]
    count_llm = prompt.count("{temp_state.llm_context}")
    count_kb = prompt.count("{temp_state.kb_section}")
    assert count_llm == 1, f"{{temp_state.llm_context}} must appear exactly once, found {count_llm}"
    assert count_kb == 1, f"{{temp_state.kb_section}} must appear exactly once, found {count_kb}"


def test_prompt_forbids_drug_names(graph):
    """Prompt must explicitly prohibit drug NAMES (not just doses).

    Original #24 acceptance extended: naming specific drugs is as unsafe as
    prescribing doses in an unreviewed educational chatbot.
    """
    nodes, _ = graph
    prompt = _by_name(nodes, "llm")["data"]["params"]["prompt"].lower()
    assert "drug" in prompt, "Prompt must explicitly address drugs"
    # Must have a line that pairs 'drug' with 'name' (not just 'dose' alone)
    assert any("drug" in line and "name" in line for line in prompt.split("\n")), (
        "Prompt must explicitly prohibit naming drugs (e.g. 'name or dose drugs'), not only state doses"
    )


def test_prompt_forbids_invented_urls(graph):
    """Prompt must forbid inventing URLs or links."""
    nodes, _ = graph
    prompt = _by_name(nodes, "llm")["data"]["params"]["prompt"].lower()
    has_url_term = any(phrase in prompt for phrase in ["url", "urls", "link"])
    assert has_url_term, "Prompt must forbid inventing URLs or links"
    for line in prompt.split("\n"):
        if any(phrase in line for phrase in ["url", "link"]):
            assert any(neg in line for neg in ("not", "never", "no ", "must not", "invent")), (
                f"URL/link reference appears without a prohibition: {line!r}"
            )


def test_prompt_has_secondary_urgency_instruction(graph):
    """Prompt must carry an urgency instruction beyond the deterministic danger-sign gate.

    The gate handles recognised patterns; the LLM must be instructed to advise
    prompt care-seeking for distress not caught deterministically.
    """
    nodes, _ = graph
    prompt = _by_name(nodes, "llm")["data"]["params"]["prompt"].lower()
    assert any(phrase in prompt for phrase in ["urgency", "urgent", "distress", "seek care"]), (
        "Prompt must include secondary urgency guidance for signs not caught by the deterministic danger-sign gate"
    )


def test_prompt_has_explicit_language_preference_variable(graph):
    """Prompt must reference {participant_data.language_preference} explicitly.

    {temp_state.llm_context} carries the language instruction from registration,
    but the OCS template variable makes the saved preference visible at review time
    and reinforces it as the primary language signal.
    """
    nodes, _ = graph
    prompt = _by_name(nodes, "llm")["data"]["params"]["prompt"]
    assert "{participant_data.language_preference}" in prompt, (
        "Prompt must include {participant_data.language_preference} to make the "
        "saved EN/SW preference explicit in the system message"
    )


def test_committed_pipeline_is_up_to_date():
    committed = json.loads(COMMITTED_PIPELINE.read_text())
    assert committed == build_pipeline(llm_provider_id=0, llm_provider_model_id=0), (
        "Run: python -m ocs.build_pipeline --write"
    )
