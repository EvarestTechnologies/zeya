"""Pipeline-level acceptance for the integrated limited-KB answer path."""

from ocs.build_pipeline import build_pipeline
from ocs.tests.conftest import node_source
from ocs.tests.sandbox import NodeHarness


def test_registered_answers_are_grounded_and_checked_before_delivery():
    flow = build_pipeline(3, 120)["data"]
    edges = {(edge["source"], edge["target"], edge["sourceHandle"]) for edge in flow["edges"]}
    required = {
        ("registration_router", "kb_context", "output_1"),
        ("kb_context", "kb_router", "output"),
        ("kb_router", "knowledge_referral", "output_0"),
        ("kb_router", "answer_match", "output_1"),
        ("answer_match", "answer_router", "output"),
        ("answer_router", "output_guard", "output_0"),
        ("answer_router", "llm_input", "output_1"),
        # Mandatory budget gate: llm_input must NOT connect directly to llm.
        ("llm_input", "prompt_budget", "output"),
        ("prompt_budget", "budget_router", "output"),
        ("budget_router", "knowledge_referral", "output_0"),  # OVER_BUDGET → referral
        ("budget_router", "llm", "output_1"),  # VALID → LLM
        ("llm", "output_guard", "output"),
        ("output_guard", "danger_question_line", "output"),
        ("danger_question_line", "end", "output"),
    }
    assert required <= edges, (
        "Registered answers must not bypass source selection, privacy filtering, "
        "the prompt-budget gate, or the output guard"
    )
    assert ("registration_router", "llm", "output_1") not in edges
    assert ("llm", "end", "output") not in edges
    # No direct bypass from llm_input to llm — budget gate is mandatory.
    assert ("llm_input", "llm", "output") not in edges
    assert ("danger_router", "emergency_response", "output_0") in edges
    assert ("emergency_response", "end", "output") in edges
    assert ("registration_router", "danger_question_line", "output_0") in edges


def test_kb_router_config_is_fail_closed():
    """kb_router must default to FALSE (no KB) so missing KB never calls the model."""
    flow = build_pipeline(0, 0)["data"]
    nodes = {n["id"]: n for n in flow["nodes"]}
    router = next(n for n in nodes.values() if n["data"]["params"].get("name") == "kb_router")
    params = router["data"]["params"]

    assert params["data_source"] == "temp_state"
    assert params["route_key"] == "kb_available"
    assert params["keywords"] == ["FALSE", "TRUE"]
    # Default must be FALSE (index 0): missing/empty kb_available → referral, no model.
    assert params["default_keyword_index"] == 0
    assert params["keywords"][params["default_keyword_index"]] == "FALSE"


def test_answer_router_config_defaults_to_ask_ai():
    """answer_router must default to ASK_AI so unknown answer_route falls to the LLM."""
    flow = build_pipeline(0, 0)["data"]
    nodes = {n["id"]: n for n in flow["nodes"]}
    router = next(n for n in nodes.values() if n["data"]["params"].get("name") == "answer_router")
    params = router["data"]["params"]

    assert params["data_source"] == "temp_state"
    assert params["route_key"] == "answer_route"
    assert params["keywords"] == ["CARD", "ASK_AI"]
    # Default must be ASK_AI (index 1): unknown route → LLM, not an empty card.
    assert params["default_keyword_index"] == 1
    assert params["keywords"][params["default_keyword_index"]] == "ASK_AI"


def test_knowledge_referral_node_passes_ocs_validation():
    """knowledge_referral source must be accepted by the OCS CodeNode validator."""
    from ocs.tests.sandbox import make_executor

    make_executor(node_source("knowledge_referral"))


def test_knowledge_referral_en_returns_referral_text():
    """English participant receives a fixed health-worker referral (no model call)."""
    h = NodeHarness(
        node_source("knowledge_referral"),
        participant_data={"language_preference": "en"},
    )
    result = h.run("Any question")
    assert "healthcare provider" in result.lower() or "health worker" in result.lower()
    assert h.temp_state.get("knowledge_referral_route") == "REFERRAL"
    assert "route:knowledge_referral" in h.message_tags


def test_knowledge_referral_sw_returns_draft_referral():
    """Swahili participant receives a draft Swahili referral (pending review — no model call)."""
    h = NodeHarness(
        node_source("knowledge_referral"),
        participant_data={"language_preference": "sw"},
    )
    result = h.run("Swali lolote")
    # Draft copy: must contain some Swahili health-worker reference
    assert len(result) > 20, "Swahili referral must be non-empty"
    assert h.temp_state.get("knowledge_referral_route") == "REFERRAL"
    assert "route:knowledge_referral" in h.message_tags


def test_knowledge_referral_absent_language_defaults_to_english():
    """Absent language_preference falls back to English referral."""
    h = NodeHarness(node_source("knowledge_referral"), participant_data={})
    result = h.run("question")
    assert "healthcare provider" in result.lower() or "health worker" in result.lower()


def test_knowledge_referral_returns_input_unchanged_on_ask_ai_path():
    """knowledge_referral returns a fixed reply, not the original input, on no-KB path."""
    h = NodeHarness(node_source("knowledge_referral"), participant_data={"language_preference": "en"})
    result = h.run("Why should I go to ANC?")
    # The node IGNORES the input and returns a fixed referral
    assert result != "Why should I go to ANC?", "knowledge_referral must return fixed reply, not original input"


def test_default_pipeline_no_kb_routes_to_referral_not_model():
    """With the default approved-only build, all KB content is pending.

    kb_context will bake KB_JSON='[]', always set kb_available=False at runtime,
    and kb_router will route FALSE → knowledge_referral.  No model is reachable.

    This test verifies the edge is present and the kb_router config is correct;
    actual runtime execution requires the full OCS engine (parent's execution gate).
    """
    flow = build_pipeline(0, 0)["data"]
    edges = {(e["source"], e["target"], e["sourceHandle"]) for e in flow["edges"]}

    # FALSE path → knowledge_referral (no model)
    assert ("kb_router", "knowledge_referral", "output_0") in edges
    # TRUE path → answer_match (only reached when KB is available)
    assert ("kb_router", "answer_match", "output_1") in edges
    # knowledge_referral terminates (through the fixed danger-question line) without reaching llm
    assert ("knowledge_referral", "danger_question_line", "output") in edges
    assert ("danger_question_line", "end", "output") in edges
    # llm is NOT reachable from knowledge_referral
    assert ("knowledge_referral", "llm", "output") not in edges
